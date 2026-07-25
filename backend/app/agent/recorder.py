"""Persists everything that happens in a voice session to Postgres.

The LiveKit pipeline emits events (transcripts, conversation items, metrics)
on the realtime path; this recorder is the boundary between that hot path and
the database. Event callbacks only buffer in memory; actual writes happen in
their own tasks so a slow INSERT can never add latency to the audio loop.
"""

import asyncio
import uuid
from datetime import UTC, datetime
from typing import Any

import structlog
from livekit.agents import metrics as lk_metrics
from sqlalchemy import update
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models import (
    AgentState,
    AgentStateEvent,
    Conversation,
    ConversationStatus,
    ConversationTurn,
    TurnLatencyMetric,
    TurnRole,
)

log = structlog.get_logger()

MAX_BUFFERED_PARTIALS = 200


class ConversationRecorder:
    def __init__(self, session_factory: async_sessionmaker, conversation_id: uuid.UUID) -> None:
        self._sessions = session_factory
        self.conversation_id = conversation_id
        # Serializes turn writes so turn_index stays gapless and ordered even
        # though events arrive from concurrent callbacks.
        self._lock = asyncio.Lock()
        self._turn_index = 0
        self._current_state: AgentState | None = None
        self._partials: list[str] = []
        # Latest metrics per stage; flushed onto the next assistant turn.
        self._pending_metrics: dict[str, Any] = {}

    async def start(self) -> None:
        async with self._sessions() as s:
            await s.execute(
                update(Conversation)
                .where(Conversation.id == self.conversation_id)
                .values(started_at=datetime.now(UTC), status=ConversationStatus.ACTIVE)
            )
            await s.commit()

    # -- buffering (called synchronously from pipeline event handlers) --------

    def buffer_partial(self, transcript: str, is_final: bool) -> None:
        if not is_final and len(self._partials) < MAX_BUFFERED_PARTIALS:
            self._partials.append(transcript)

    def buffer_metrics(self, m: lk_metrics.AgentMetrics) -> None:
        if isinstance(m, lk_metrics.EOUMetrics):
            self._pending_metrics["eou"] = {
                "end_of_utterance_delay_s": m.end_of_utterance_delay,
                "transcription_delay_s": m.transcription_delay,
            }
        elif isinstance(m, lk_metrics.LLMMetrics):
            self._pending_metrics["llm"] = {"ttft_s": m.ttft, "duration_s": m.duration}
        elif isinstance(m, lk_metrics.TTSMetrics):
            self._pending_metrics["tts"] = {"ttfb_s": m.ttfb, "duration_s": m.duration}
        elif isinstance(m, lk_metrics.STTMetrics):
            self._pending_metrics["stt"] = {"duration_s": m.duration}

    # -- persistence ----------------------------------------------------------

    async def record_turn(self, role: str, content: str, interrupted: bool) -> None:
        async with self._lock:
            index = self._turn_index
            self._turn_index += 1
            extra: dict[str, Any] | None = None
            if role == TurnRole.USER and self._partials:
                extra = {"partials": self._partials}
                self._partials = []
            metrics_snapshot = self._pending_metrics if role == TurnRole.ASSISTANT else None
            if role == TurnRole.ASSISTANT:
                self._pending_metrics = {}

        async with self._sessions() as s:
            turn = ConversationTurn(
                conversation_id=self.conversation_id,
                turn_index=index,
                role=TurnRole(role),
                content=content,
                interrupted=interrupted,
                extra=extra,
            )
            s.add(turn)
            await s.flush()  # assigns turn.id for the latency row

            if metrics_snapshot:
                s.add(self._build_latency_row(turn.id, metrics_snapshot))
            await s.commit()
        log.info("turn_recorded", index=index, role=role, interrupted=interrupted)

    def _build_latency_row(self, turn_id: uuid.UUID, m: dict[str, Any]) -> TurnLatencyMetric:
        def ms(section: str, key: str) -> int | None:
            value = m.get(section, {}).get(key)
            return round(value * 1000) if value is not None else None

        stt_final = ms("eou", "transcription_delay_s")
        llm_ttft = ms("llm", "ttft_s")
        tts_ttfb = ms("tts", "ttfb_s")
        # Perceived response latency: user stops speaking -> final transcript
        # -> first LLM token -> first synthesized audio.
        parts = [p for p in (stt_final, llm_ttft, tts_ttfb) if p is not None]
        total = sum(parts) if parts else None
        return TurnLatencyMetric(
            turn_id=turn_id,
            conversation_id=self.conversation_id,
            stt_final_ms=stt_final,
            llm_first_token_ms=llm_ttft,
            llm_total_ms=ms("llm", "duration_s"),
            tts_first_audio_ms=tts_ttfb,
            total_response_ms=total,
            raw=m,
        )

    async def record_state(
        self, to_state: AgentState, reason: str | None = None
    ) -> None:
        async with self._sessions() as s:
            s.add(
                AgentStateEvent(
                    conversation_id=self.conversation_id,
                    from_state=self._current_state,
                    to_state=to_state,
                    reason=reason,
                )
            )
            await s.commit()
        self._current_state = to_state

    async def finish(self, status: ConversationStatus, outcome: str | None = None) -> None:
        final_state = (
            AgentState.COMPLETED if status == ConversationStatus.COMPLETED else AgentState.FAILED
        )
        await self.record_state(final_state, reason=outcome)
        async with self._sessions() as s:
            await s.execute(
                update(Conversation)
                .where(Conversation.id == self.conversation_id)
                .values(ended_at=datetime.now(UTC), status=status, outcome=outcome)
            )
            await s.commit()
        log.info("conversation_finished", status=status, turns=self._turn_index)
