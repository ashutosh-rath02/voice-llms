"""Tools the voice agent can call mid-call.

search_knowledge_base is the Phase 2b bridge between the orchestrator and
the retrieval layer built in Phase 2a: the LLM decides when a question needs
grounding, calls this tool, and every call — including ones that find
nothing — is logged as a RetrievalEvent against the real conversation via
app.knowledge.retrieval.hybrid_search.
"""

from dataclasses import dataclass

import structlog
from livekit.agents import RunContext, function_tool
from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.config import Settings
from app.knowledge.retrieval import hybrid_search

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
