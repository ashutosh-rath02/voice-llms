"""Read-model schemas for the replay views. These flatten the ORM graph into
exactly what the UI needs — no lazy-loading surprises, no over-fetching."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class LatencyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    stt_final_ms: int | None
    llm_first_token_ms: int | None
    tts_first_audio_ms: int | None
    total_response_ms: int | None


class TurnOut(BaseModel):
    turn_index: int
    role: str
    content: str
    language: str | None
    interrupted: bool
    created_at: datetime
    latency: LatencyOut | None
    partials: list[str]


class StateEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    from_state: str | None
    to_state: str
    reason: str | None
    created_at: datetime


class RetrievalResultOut(BaseModel):
    chunk_id: str
    document_title: str
    document_url: str | None
    score: float
    vector_rank: int | None
    fts_rank: int | None


class RetrievalEventOut(BaseModel):
    query: str
    strategy: str
    latency_ms: int
    created_at: datetime
    results: list[RetrievalResultOut]


class ConversationSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    room_name: str | None
    channel: str
    status: str
    outcome: str | None
    customer_id: uuid.UUID | None
    customer_name: str | None = None
    started_at: datetime | None
    ended_at: datetime | None
    created_at: datetime


class ConversationDetail(ConversationSummary):
    agent_version_label: str
    turns: list[TurnOut]
    state_events: list[StateEventOut]
    retrieval_events: list[RetrievalEventOut]
