import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source: str
    path: str
    title: str
    url: str | None
    status: str
    chunk_count: int
    last_indexed_at: datetime | None


class SearchRequest(BaseModel):
    query: str
    top_k: int | None = None


class SearchResultOut(BaseModel):
    chunk_id: str
    document_id: str
    document_title: str
    document_url: str | None
    heading: str | None
    content: str
    score: float
    vector_rank: int | None
    fts_rank: int | None


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResultOut]
    latency_ms: int
