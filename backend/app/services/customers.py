"""Real, confirmation-gated customer-record actions."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.confirmation import register_executor
from app.models import ContactType, CustomerContact

TOOL_NAME = "update_contact_info"


async def execute_update_contact(
    session: AsyncSession, arguments: dict[str, Any]
) -> dict[str, Any]:
    """PRD 6.9: 'Updating customer contact information' — one of the actions
    that must never run without explicit confirmation. By the time this runs,
    confirm_tool_execution has already recorded that confirmation."""
    customer_id = arguments["customer_id"]
    contact_type = ContactType(arguments["contact_type"])
    value = arguments["value"]

    existing = (
        await session.execute(
            select(CustomerContact).where(
                CustomerContact.customer_id == customer_id,
                CustomerContact.contact_type == contact_type,
            )
        )
    ).scalar_one_or_none()

    if existing:
        existing.value = value
    else:
        session.add(
            CustomerContact(customer_id=customer_id, contact_type=contact_type, value=value)
        )

    return {"summary": f"Updated your {contact_type.value} on file to {value}."}


register_executor(TOOL_NAME, execute_update_contact)
