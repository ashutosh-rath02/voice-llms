import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import (
    Base,
    CreatedAtMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    str_enum,
)

if TYPE_CHECKING:
    from app.models.customer import Customer


class ConversationChannel(enum.StrEnum):
    BROWSER = "browser"
    PHONE = "phone"  # Phase 4


class ConversationStatus(enum.StrEnum):
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    ABANDONED = "abandoned"


class AgentState(enum.StrEnum):
    """Orchestrator states from PRD §6.5. Milestone 1 uses only a few
    (GREETING, COMPLETED, FAILED); the rest activate with later phases."""

    GREETING = "greeting"
    CONSENT = "consent"
    CUSTOMER_IDENTIFICATION = "customer_identification"
    ISSUE_DISCOVERY = "issue_discovery"
    INFORMATION_COLLECTION = "information_collection"
    KNOWLEDGE_RETRIEVAL = "knowledge_retrieval"
    ACTION_PROPOSAL = "action_proposal"
    USER_CONFIRMATION = "user_confirmation"
    TOOL_EXECUTION = "tool_execution"
    RESOLUTION_CONFIRMATION = "resolution_confirmation"
    HUMAN_HANDOFF = "human_handoff"
    COMPLETED = "completed"
    FAILED = "failed"


class TurnRole(enum.StrEnum):
    USER = "user"
    ASSISTANT = "assistant"


class Conversation(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """One voice session, browser or phone, from join to hang-up."""

    __tablename__ = "conversations"

    # Nullable: Phase 4 phone callers are identified mid-call (or never);
    # browser sessions always set it from the authenticated user.
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    # Set by the lookup_customer tool once the agent identifies the caller —
    # distinct from user_id (platform login) since a caller may authenticate
    # by voice (email/phone) without ever having a web account.
    customer_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("customers.id"), index=True)
    agent_version_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agent_versions.id"))

    channel: Mapped[ConversationChannel] = mapped_column(str_enum(ConversationChannel))
    status: Mapped[ConversationStatus] = mapped_column(
        str_enum(ConversationStatus), default=ConversationStatus.ACTIVE, index=True
    )
    # LiveKit room name; unique per session so the agent worker can map a room
    # joining event back to this row.
    room_name: Mapped[str | None] = mapped_column(String(255), unique=True)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Filled at session end: what actually happened, for the dashboard and evals.
    outcome: Mapped[str | None] = mapped_column(String(64))
    summary: Mapped[str | None] = mapped_column(Text)

    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # One-directional: Customer doesn't need to enumerate all its calls right
    # now, so no back_populates. String ref resolves against the shared
    # declarative registry — no import of Customer needed here.
    customer: Mapped["Customer | None"] = relationship(viewonly=True)

    turns: Mapped[list["ConversationTurn"]] = relationship(
        back_populates="conversation", order_by="ConversationTurn.turn_index"
    )
    state_events: Mapped[list["AgentStateEvent"]] = relationship(
        back_populates="conversation", order_by="AgentStateEvent.created_at"
    )


class ConversationTurn(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    """One utterance by one party, with its final transcript.

    Assistant turns store what was actually *spoken* — after a barge-in the
    content is truncated to the audio that played, and `interrupted` is set,
    so the stored transcript matches what the user really heard.
    """

    __tablename__ = "conversation_turns"
    __table_args__ = (UniqueConstraint("conversation_id", "turn_index"),)

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("conversations.id"), index=True
    )
    turn_index: Mapped[int] = mapped_column(Integer)
    role: Mapped[TurnRole] = mapped_column(str_enum(TurnRole))
    content: Mapped[str] = mapped_column(Text)
    language: Mapped[str | None] = mapped_column(String(16))  # per-turn, PRD §7.4
    interrupted: Mapped[bool] = mapped_column(default=False)

    speech_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    speech_ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Provider metadata that doesn't warrant columns yet: partial-transcript
    # timeline, STT confidence, model ids for this turn.
    extra: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    conversation: Mapped[Conversation] = relationship(back_populates="turns")
    latency: Mapped["TurnLatencyMetric | None"] = relationship(back_populates="turn")


class AgentStateEvent(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    """Append-only log of orchestrator state transitions (PRD: 'transitions
    must be logged'). Powers the state timeline in the replay view."""

    __tablename__ = "agent_state_events"
    __table_args__ = (
        Index("ix_agent_state_events_conversation_created", "conversation_id", "created_at"),
    )

    conversation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("conversations.id"))
    from_state: Mapped[AgentState | None] = mapped_column(str_enum(AgentState))
    to_state: Mapped[AgentState] = mapped_column(str_enum(AgentState))
    reason: Mapped[str | None] = mapped_column(String(255))

    conversation: Mapped[Conversation] = relationship(back_populates="state_events")


class TurnLatencyMetric(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    """Latency breakdown for one assistant turn (PRD §7.3).

    All values are milliseconds measured from the end of the user's speech
    (the moment the user stops talking is what response latency is felt from).
    Columns hold the marks the dashboard aggregates (p50/p95 via SQL);
    `raw` keeps every mark we captured for debugging.
    """

    __tablename__ = "turn_latency_metrics"

    turn_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("conversation_turns.id"), unique=True)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("conversations.id"), index=True
    )

    stt_first_partial_ms: Mapped[int | None] = mapped_column(Integer)
    stt_final_ms: Mapped[int | None] = mapped_column(Integer)
    llm_first_token_ms: Mapped[int | None] = mapped_column(Integer)
    llm_total_ms: Mapped[int | None] = mapped_column(Integer)
    tts_first_audio_ms: Mapped[int | None] = mapped_column(Integer)
    total_response_ms: Mapped[int | None] = mapped_column(Integer)

    raw: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    turn: Mapped[ConversationTurn] = relationship(back_populates="latency")
