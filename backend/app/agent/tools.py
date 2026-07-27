"""Tools the voice agent can call mid-call.

search_knowledge_base is the Phase 2b bridge between the orchestrator and
the retrieval layer built in Phase 2a: the LLM decides when a question needs
grounding, calls this tool, and every call — including ones that find
nothing — is logged as a RetrievalEvent against the real conversation via
app.knowledge.retrieval.hybrid_search.
"""

import re
from dataclasses import dataclass

import structlog
from livekit.agents import RunContext, function_tool
from openai import AsyncOpenAI
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.config import Settings
from app.knowledge.retrieval import hybrid_search
from app.models import (
    ContactType,
    Conversation,
    Customer,
    CustomerContact,
    CustomerProduct,
    CustomerProductStatus,
    ProductOrService,
)

log = structlog.get_logger()


@dataclass
class SessionData:
    """Per-call context threaded into every tool via AgentSession(userdata=...)."""

    db_sessions: async_sessionmaker
    openai_client: AsyncOpenAI
    settings: Settings
    conversation_id: str


async def run_knowledge_search(data: SessionData, query: str) -> str:
    """Business logic behind the tool, kept free of LiveKit's RunContext so it
    can be called directly — by the live tool wrapper below, or by tests/evals
    that don't want to construct a real AgentSession just to exercise it."""
    async with data.db_sessions() as session:
        results = await hybrid_search(
            session,
            data.openai_client,
            data.settings,
            query,
            conversation_id=data.conversation_id,
        )
    log.info("knowledge_tool_called", query=query, n_results=len(results))

    if not results:
        return "No relevant documentation was found for this query."

    parts = []
    for r in results:
        snippet = r.content if len(r.content) <= 600 else r.content[:600] + "…"
        parts.append(f"Source: {r.document_title}\n{snippet}")
    return "\n\n---\n\n".join(parts)


@function_tool(
    description=(
        "Search the product support knowledge base for troubleshooting steps, "
        "setup instructions, or configuration details. Call this before answering "
        "any question about how to set up, configure, or fix a specific device or "
        "integration — do not answer from memory. If the results are not relevant "
        "to what the user asked, say you don't have that information and offer to "
        "get a human involved, rather than guessing."
    )
)
async def search_knowledge_base(ctx: RunContext[SessionData], query: str) -> str:
    """Args: query: the user's question, in their own words."""
    return await run_knowledge_search(ctx.userdata, query)


def _digits_only(value: str) -> str:
    return re.sub(r"\D", "", value)


async def run_customer_lookup(data: SessionData, contact_value: str) -> str:
    """Find the customer by email or phone and stamp the match onto the
    conversation row, so replay/dashboard show who the call was about.

    Phone matching compares digits only (STT renders "+91 98765 43210" and
    "919876543210" differently) — email matches case-insensitively.
    """
    normalized_email = contact_value.strip().lower()
    digits = _digits_only(contact_value)

    async with data.db_sessions() as session:
        contact = (
            await session.execute(
                select(CustomerContact).where(
                    func.lower(CustomerContact.value) == normalized_email
                )
            )
        ).scalar_one_or_none()

        if contact is None and digits:
            phone_contacts = (
                await session.execute(
                    select(CustomerContact).where(CustomerContact.contact_type == ContactType.PHONE)
                )
            ).scalars().all()
            contact = next(
                (c for c in phone_contacts if _digits_only(c.value) == digits), None
            )

        if contact is None:
            log.info("customer_lookup_miss", conversation_id=data.conversation_id)
            return "No customer account was found with that email or phone number."

        customer = await session.get(Customer, contact.customer_id)
        product_names = (
            await session.execute(
                select(ProductOrService.name)
                .join(CustomerProduct, CustomerProduct.product_id == ProductOrService.id)
                .where(
                    CustomerProduct.customer_id == customer.id,
                    CustomerProduct.status == CustomerProductStatus.ACTIVE,
                )
            )
        ).scalars().all()

        await session.execute(
            update(Conversation)
            .where(Conversation.id == data.conversation_id)
            .values(customer_id=customer.id)
        )
        await session.commit()

    log.info(
        "customer_identified",
        conversation_id=data.conversation_id,
        customer_id=str(customer.id),
    )
    devices = ", ".join(product_names) if product_names else "no registered devices"
    return f"Identified customer: {customer.full_name}. Registered devices: {devices}."


@function_tool(
    description=(
        "Look up the caller's account by the email address or phone number they "
        "give you, to confirm their identity and see what devices they have "
        "registered. Call this once, early in the conversation, after asking the "
        "caller for their email or phone number — do not call it before they have "
        "given you one. If it finds no account, tell them and continue helping "
        "them anyway; an account is not required to get support."
    )
)
async def lookup_customer(ctx: RunContext[SessionData], contact_value: str) -> str:
    """Args: contact_value: the email or phone number the caller provided."""
    return await run_customer_lookup(ctx.userdata, contact_value)
