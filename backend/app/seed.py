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
from app.models import AgentVersion, AgentVersionStatus, ProviderConfig, Role, RoleName, User

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
        "status": AgentVersionStatus.ACTIVE,
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
]

# Exactly one AgentVersion is ACTIVE at a time; this is the one seed() enforces.
ACTIVE_VERSION_LABEL = "v0.2.0"

DEFAULT_TURN_DETECTION = {
    "name": "turn_detection.default",
    "description": "Endpointing thresholds for the voice pipeline (PRD 7.2)",
    "config": {
        "min_endpointing_delay_s": 0.5,
        "max_endpointing_delay_s": 6.0,
        "min_interruption_duration_s": 0.5,
    },
}


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
