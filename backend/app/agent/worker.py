"""LiveKit agent worker: the realtime voice pipeline.

Run from backend/:
    python -m app.agent.worker dev

The worker registers with LiveKit Cloud and is dispatched into rooms as they
are created. Pipeline per session: Silero VAD -> Deepgram STT -> LLM
(OpenAI or Groq, chosen by the active agent version) -> ElevenLabs TTS,
with barge-in handled by the AgentSession. Everything that happens is
persisted through ConversationRecorder.
"""

import asyncio

import structlog
from livekit import agents
from livekit.agents import Agent, AgentSession, JobContext, WorkerOptions, cli
from livekit.plugins import deepgram, elevenlabs, groq, openai, silero
from openai import AsyncOpenAI
from sqlalchemy import select

from app.agent.recorder import ConversationRecorder
from app.agent.tools import SessionData, lookup_customer, search_knowledge_base
from app.core import db
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging
from app.models import (
    AgentState,
    AgentVersion,
    AgentVersionStatus,
    Conversation,
    ConversationChannel,
    ConversationStatus,
    ProviderConfig,
)

log = structlog.get_logger()


def build_llm(agent_version: AgentVersion, settings: Settings):
    """The active agent version decides which LLM serves the call —
    switching provider is a database row change, not a code change."""
    if agent_version.llm_provider == "groq":
        return groq.LLM(model=agent_version.llm_model, api_key=settings.groq_api_key)
    return openai.LLM(model=agent_version.llm_model, api_key=settings.openai_api_key)


async def load_session_context(sessions, room_name: str):
    """Fetch (conversation, agent_version, turn_detection_config) for a room.

    Rooms created outside our API (e.g. the LiveKit playground during testing)
    have no conversation row yet — we create one on the fly so even ad-hoc
    test calls are fully persisted, per the no-fake-data rule.
    """
    async with sessions() as s:
        agent_version = (
            await s.execute(
                select(AgentVersion)
                .where(AgentVersion.status == AgentVersionStatus.ACTIVE)
                .order_by(AgentVersion.created_at.desc())
            )
        ).scalars().first()
        if agent_version is None:
            raise RuntimeError("No active agent_version in database — run app.seed")

        conversation = (
            await s.execute(select(Conversation).where(Conversation.room_name == room_name))
        ).scalar_one_or_none()
        if conversation is None:
            conversation = Conversation(
                agent_version_id=agent_version.id,
                channel=ConversationChannel.BROWSER,
                room_name=room_name,
            )
            s.add(conversation)
            await s.commit()
            log.info("conversation_created_adhoc", room=room_name)

        turn_config_row = (
            await s.execute(
                select(ProviderConfig).where(
                    ProviderConfig.name == "turn_detection.default",
                    ProviderConfig.is_active.is_(True),
                )
            )
        ).scalar_one_or_none()
        turn_config = turn_config_row.config if turn_config_row else {}
        return conversation, agent_version, turn_config


async def entrypoint(ctx: JobContext) -> None:
    settings = get_settings()
    engine = db.create_engine(settings)
    sessions = db.create_session_factory(engine)
    openai_client = AsyncOpenAI(api_key=settings.openai_api_key)

    conversation, agent_version, turn_config = await load_session_context(
        sessions, ctx.room.name
    )
    recorder = ConversationRecorder(sessions, conversation.id)
    await recorder.start()
    session_data = SessionData(
        db_sessions=sessions,
        openai_client=openai_client,
        settings=settings,
        conversation_id=str(conversation.id),
    )
    log.info(
        "voice_session_starting",
        room=ctx.room.name,
        conversation_id=str(conversation.id),
        agent_version=agent_version.version_label,
        llm=f"{agent_version.llm_provider}/{agent_version.llm_model}",
    )

    session = AgentSession[SessionData](
        userdata=session_data,
        vad=ctx.proc.userdata.get("vad") or silero.VAD.load(),
        stt=deepgram.STT(
            model=agent_version.stt_model,
            language="en",  # Phase 5 widens this to hi / multi with eval coverage
            api_key=settings.deepgram_api_key,
        ),
        llm=build_llm(agent_version, settings),
        tts=elevenlabs.TTS(model=agent_version.tts_model, api_key=settings.elevenlabs_api_key),
        min_endpointing_delay=turn_config.get("min_endpointing_delay_s", 0.5),
        max_endpointing_delay=turn_config.get("max_endpointing_delay_s", 6.0),
    )

    # Event handlers must be synchronous and fast: buffer, spawn a task, return.
    @session.on("user_input_transcribed")
    def on_transcribed(ev) -> None:
        recorder.buffer_partial(ev.transcript, ev.is_final)

    @session.on("conversation_item_added")
    def on_item_added(ev) -> None:
        item = ev.item
        if item.role not in ("user", "assistant"):
            return
        asyncio.create_task(
            recorder.record_turn(
                role=item.role,
                content=item.text_content or "",
                interrupted=bool(getattr(item, "interrupted", False)),
            )
        )

    @session.on("metrics_collected")
    def on_metrics(ev) -> None:
        recorder.buffer_metrics(ev.metrics)

    async def finalize() -> None:
        try:
            await recorder.finish(ConversationStatus.COMPLETED, outcome="session_ended")
        finally:
            await openai_client.close()
            await engine.dispose()

    ctx.add_shutdown_callback(finalize)

    await ctx.connect()
    agent = Agent(
        instructions=agent_version.system_prompt,
        tools=[search_knowledge_base, lookup_customer],
    )
    await session.start(agent=agent, room=ctx.room)
    await recorder.record_state(AgentState.GREETING, reason="session_started")
    await session.generate_reply(
        instructions="Greet the caller briefly and ask how you can help."
    )


def prewarm(proc: agents.JobProcess) -> None:
    # Loading the Silero VAD model takes ~1s; doing it once per process at
    # startup keeps it off the critical path of every call.
    proc.userdata["vad"] = silero.VAD.load()


if __name__ == "__main__":
    settings = get_settings()
    configure_logging(settings.log_level, json_output=settings.app_env != "dev")
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_fnc=prewarm,
            ws_url=settings.livekit_url,
            api_key=settings.livekit_api_key,
            api_secret=settings.livekit_api_secret,
        )
    )
