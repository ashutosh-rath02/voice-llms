"""Idempotent seed data: roles, agent versions, default turn-detection config.

Run with:  python -m app.seed

Safe to run repeatedly — inserts use ON CONFLICT DO NOTHING on natural unique
keys (role name, version label, config name), so existing rows are never
duplicated or overwritten. Per the PRD, seed data goes through the same
database as production writes; the dev login user is seeded in the auth chunk
where password hashing lives.

Agent versions are append-only history: once a conversation references a
version, its prompt/model config never changes — a new capability ships as a
new version_label, and `seed()` flips exactly one row to ACTIVE. `status` is
the one mutable field on this table by design (see models/agent.py).
"""

import asyncio

import structlog
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core import db, security
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging
from app.models import (
    AgentVersion,
    AgentVersionStatus,
    ContactType,
    Customer,
    CustomerContact,
    CustomerProduct,
    ProductOrService,
    ProviderConfig,
    Role,
    RoleName,
    User,
)

log = structlog.get_logger()

ROLES = [
    {"name": RoleName.ADMIN, "description": "Platform engineer: providers, deploys, evals"},
    {"name": RoleName.SUPPORT_MANAGER, "description": "Metrics, policies, release review"},
    {"name": RoleName.SUPPORT_AGENT, "description": "Live calls, takeover, tickets"},
    {"name": RoleName.CUSTOMER, "description": "Own conversations only"},
]

VOICE_STYLE_RULES = (
    "You are speaking with the user over live audio, so keep every response short — "
    "one to three sentences — and conversational. Never use markdown, bullet points, "
    "or emoji. Spell out numbers and identifiers digit by digit when confirming them. "
    "If you did not understand the user, ask them to repeat rather than guessing."
)

AGENT_VERSIONS = [
    {
        "version_label": "v0.1.0",
        "status": AgentVersionStatus.ACTIVE,  # historical; demoted below once v0.2.0 exists
        "system_prompt": (
            f"You are a friendly customer-support voice agent. {VOICE_STYLE_RULES} "
            "If the user asks for something you cannot do yet, say so honestly."
        ),
        "llm_provider": "openai",
        "llm_model": "gpt-4o-mini",
        "stt_provider": "deepgram",
        "stt_model": "nova-2",
        "tts_provider": "elevenlabs",
        "tts_model": "eleven_flash_v2_5",
        "tts_voice": "pending-selection",
        "config": {"llm_temperature": 0.4},
    },
    {
        "version_label": "v0.2.0",
        "status": AgentVersionStatus.ACTIVE,  # historical; demoted below once v0.3.0 exists
        "system_prompt": (
            "You are a friendly customer-support voice agent for smart-home device "
            f"support. {VOICE_STYLE_RULES}\n\n"
            "You have a search_knowledge_base tool over real product documentation. "
            "Whenever the user asks how to set up, configure, or fix a specific device "
            "or integration, call the tool with their question before answering — do "
            "not answer setup steps, settings, or troubleshooting details from memory. "
            "When you answer from the tool's results, mention which product or "
            "integration the information is about so the user knows it is grounded, "
            "not guessed.\n\n"
            "If the tool finds nothing relevant, or you are not confident the results "
            "actually answer what the user asked, say plainly that you don't have "
            "reliable information on that and offer to connect them with a human "
            "support agent. Never invent setup steps, settings, or error resolutions."
        ),
        "llm_provider": "openai",
        "llm_model": "gpt-4o-mini",
        "stt_provider": "deepgram",
        "stt_model": "nova-2",
        "tts_provider": "elevenlabs",
        "tts_model": "eleven_flash_v2_5",
        "tts_voice": "pending-selection",
        "config": {"llm_temperature": 0.4},
    },
    {
        "version_label": "v0.3.0",
        "status": AgentVersionStatus.ACTIVE,  # historical; demoted below once v0.4.0 exists
        "system_prompt": (
            "You are a friendly customer-support voice agent for smart-home device "
            f"support. {VOICE_STYLE_RULES}\n\n"
            "Early in the conversation, once the caller has explained why they're "
            "calling, ask for their email address or phone number and call "
            "lookup_customer with what they give you — this confirms their identity "
            "and shows you what devices they have registered. Do not call it before "
            "they've given you a contact value, and do not insist if they'd rather "
            "not: continue helping them without an account. Once identified, use "
            "their name and registered devices naturally in conversation.\n\n"
            "You have a search_knowledge_base tool over real product documentation. "
            "Whenever the user asks how to set up, configure, or fix a specific device "
            "or integration, call the tool with their question before answering — do "
            "not answer setup steps, settings, or troubleshooting details from memory. "
            "When you answer from the tool's results, mention which product or "
            "integration the information is about so the user knows it is grounded, "
            "not guessed.\n\n"
            "If the tool finds nothing relevant, or you are not confident the results "
            "actually answer what the user asked, say plainly that you don't have "
            "reliable information on that and offer to connect them with a human "
            "support agent. Never invent setup steps, settings, or error resolutions."
        ),
        "llm_provider": "openai",
        "llm_model": "gpt-4o-mini",
        "stt_provider": "deepgram",
        "stt_model": "nova-2",
        "tts_provider": "elevenlabs",
        "tts_model": "eleven_flash_v2_5",
        "tts_voice": "pending-selection",
        "config": {"llm_temperature": 0.4},
    },
    {
        "version_label": "v0.4.0",
        "status": AgentVersionStatus.ACTIVE,
        "system_prompt": (
            "You are a friendly customer-support voice agent for smart-home device "
            f"support. {VOICE_STYLE_RULES}\n\n"
            "Early in the conversation, once the caller has explained why they're "
            "calling, ask for their email address or phone number and call "
            "lookup_customer with what they give you — this confirms their identity "
            "and shows you what devices they have registered. Do not call it before "
            "they've given you a contact value, and do not insist if they'd rather "
            "not: continue helping them without an account. Once identified, use "
            "their name and registered devices naturally in conversation.\n\n"
            "You have a search_knowledge_base tool over real product documentation. "
            "Whenever the user asks how to set up, configure, or fix a specific device "
            "or integration, call the tool with their question before answering — do "
            "not answer setup steps, settings, or troubleshooting details from memory. "
            "When you answer from the tool's results, mention which product or "
            "integration the information is about so the user knows it is grounded, "
            "not guessed.\n\n"
            "If the tool finds nothing relevant, or you are not confident the results "
            "actually answer what the user asked, say plainly that you don't have "
            "reliable information on that and offer to connect them with a human "
            "support agent. Never invent setup steps, settings, or error resolutions.\n\n"
            "If an identified caller wants to change their phone number or email on "
            "file, use propose_update_contact, then read the exact change back to "
            "them in full and ask them to confirm — for example 'just to confirm, "
            "I'll set your email to jane@example.com, is that right?'. Only call "
            "confirm_pending_action if their reply is a clear yes. A vague, unclear, "
            "or off-topic reply is not confirmation — ask again instead of guessing. "
            "If they decline or change their mind, call cancel_pending_action. Never "
            "claim a change was made before confirm_pending_action actually returns "
            "success — if it reports a problem, tell the caller honestly."
        ),
        "llm_provider": "openai",
        "llm_model": "gpt-4o-mini",
        "stt_provider": "deepgram",
        "stt_model": "nova-2",
        "tts_provider": "elevenlabs",
        "tts_model": "eleven_flash_v2_5",
        "tts_voice": "pending-selection",
        "config": {"llm_temperature": 0.4},
    },
]

# Exactly one AgentVersion is ACTIVE at a time; this is the one seed() enforces.
ACTIVE_VERSION_LABEL = "v0.4.0"

DEFAULT_TURN_DETECTION = {
    "name": "turn_detection.default",
    "description": "Endpointing thresholds for the voice pipeline (PRD 7.2)",
    "config": {
        "min_endpointing_delay_s": 0.5,
        "max_endpointing_delay_s": 6.0,
        "min_interruption_duration_s": 0.5,
    },
}

# Device catalog — names chosen to match real integrations in the ingested
# Home Assistant knowledge base, so a customer's registered product and the
# agent's retrieval results are about the same real thing end to end.
PRODUCTS = [
    {
        "name": "Zigbee Home Automation Hub",
        "category": "Hub",
        "description": "Zigbee coordinator for pairing Zigbee-based smart devices (ZHA).",
    },
    {
        "name": "Z-Wave USB Controller",
        "category": "Hub",
        "description": "USB Z-Wave stick used to build and control a Z-Wave mesh network.",
    },
    {
        "name": "MQTT Smart Plug",
        "category": "Switch",
        "description": "Wi-Fi smart plug that publishes state over MQTT.",
    },
    {
        "name": "Philips Hue Bridge",
        "category": "Hub",
        "description": "Bridge connecting Philips Hue smart lights to the local network.",
    },
    {
        "name": "Google Nest Thermostat",
        "category": "Climate",
        "description": "Wi-Fi connected thermostat integrated via the Google Nest account.",
    },
]

# (full_name, [(contact_type, value, is_primary), ...], [product names])
CUSTOMERS = [
    (
        "Priya Sharma",
        [
            (ContactType.EMAIL, "priya.sharma@example.com", True),
            (ContactType.PHONE, "+91-98765-43210", False),
        ],
        ["Zigbee Home Automation Hub"],
    ),
    (
        "Rahul Mehta",
        [(ContactType.EMAIL, "rahul.mehta@example.com", True)],
        ["Z-Wave USB Controller", "MQTT Smart Plug"],
    ),
    (
        "Ananya Iyer",
        [
            (ContactType.EMAIL, "ananya.iyer@example.com", True),
            (ContactType.PHONE, "+91-91234-56789", False),
        ],
        ["Philips Hue Bridge"],
    ),
    (
        "David Chen",
        [(ContactType.EMAIL, "david.chen@example.com", True)],
        ["Google Nest Thermostat"],
    ),
]


async def seed(engine: AsyncEngine, settings: Settings) -> None:
    session_factory = db.create_session_factory(engine)
    async with session_factory() as session:
        result = await session.execute(
            insert(Role).values(ROLES).on_conflict_do_nothing(index_elements=["name"])
        )
        log.info("seeded_roles", inserted=result.rowcount, skipped=len(ROLES) - result.rowcount)

        admin_role_id = (
            await session.execute(select(Role.id).where(Role.name == RoleName.ADMIN))
        ).scalar_one()
        result = await session.execute(
            insert(User)
            .values(
                email=settings.seed_admin_email,
                hashed_password=security.hash_password(settings.seed_admin_password),
                full_name="Dev Admin",
                role_id=admin_role_id,
            )
            .on_conflict_do_nothing(index_elements=["email"])
        )
        log.info("seeded_admin_user", inserted=result.rowcount, email=settings.seed_admin_email)

        for product in PRODUCTS:
            await session.execute(
                insert(ProductOrService)
                .values(**product)
                .on_conflict_do_nothing(index_elements=["name"])
            )
        product_ids = {
            p.name: p.id for p in (await session.execute(select(ProductOrService))).scalars()
        }

        customers_inserted = 0
        for full_name, contacts, product_names in CUSTOMERS:
            primary_email = next(v for _, v, is_primary in contacts if is_primary)
            already_exists = (
                await session.execute(
                    select(CustomerContact.id).where(CustomerContact.value == primary_email)
                )
            ).scalar_one_or_none()
            if already_exists:
                continue
            customer = Customer(full_name=full_name)
            session.add(customer)
            await session.flush()  # assigns customer.id for the FK rows below
            session.add_all(
                CustomerContact(
                    customer_id=customer.id, contact_type=ctype, value=value, is_primary=primary
                )
                for ctype, value, primary in contacts
            )
            session.add_all(
                CustomerProduct(customer_id=customer.id, product_id=product_ids[name])
                for name in product_names
            )
            customers_inserted += 1
        log.info(
            "seeded_customers",
            inserted=customers_inserted,
            skipped=len(CUSTOMERS) - customers_inserted,
        )

        for version in AGENT_VERSIONS:
            result = await session.execute(
                insert(AgentVersion)
                .values(**version)
                .on_conflict_do_nothing(index_elements=["version_label"])
            )
            log.info(
                "seeded_agent_version", label=version["version_label"], inserted=result.rowcount
            )

        # Enforce exactly one ACTIVE version regardless of history above —
        # status is mutable operational metadata, not part of a version's
        # immutable content.
        result = await session.execute(
            update(AgentVersion)
            .where(
                AgentVersion.version_label != ACTIVE_VERSION_LABEL,
                AgentVersion.status == AgentVersionStatus.ACTIVE,
            )
            .values(status=AgentVersionStatus.INACTIVE)
        )
        result2 = await session.execute(
            update(AgentVersion)
            .where(AgentVersion.version_label == ACTIVE_VERSION_LABEL)
            .values(status=AgentVersionStatus.ACTIVE)
        )
        log.info(
            "active_agent_version_enforced",
            active=ACTIVE_VERSION_LABEL,
            demoted=result.rowcount,
            confirmed=result2.rowcount,
        )

        result = await session.execute(
            insert(ProviderConfig)
            .values(**DEFAULT_TURN_DETECTION)
            .on_conflict_do_nothing(index_elements=["name"])
        )
        log.info("seeded_provider_config", inserted=result.rowcount)

        await session.commit()


async def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level, json_output=settings.app_env != "dev")
    engine = db.create_engine(settings)
    try:
        await seed(engine, settings)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
