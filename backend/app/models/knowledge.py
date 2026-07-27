import enum
import uuid
from datetime import datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import (
    Base,
    CreatedAtMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    str_enum,
)

# text-embedding-3-small output width; changing models means re-embedding
# everything, so the dimension is fixed here next to the schema that stores it.
EMBEDDING_DIM = 1536


class DocumentStatus(enum.StrEnum):
    PENDING = "pending"
    INDEXED = "indexed"
    FAILED = "failed"


class KnowledgeDocument(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """One source article (e.g. a Home Assistant docs page).

    (source, path) is the natural key; content_hash makes re-ingestion cheap —
    unchanged documents are skipped, changed ones get their chunks rebuilt.
    """

    __tablename__ = "knowledge_documents"
    __table_args__ = (UniqueConstraint("source", "path"),)

    source: Mapped[str] = mapped_column(String(64))  # corpus name
    path: Mapped[str] = mapped_column(String(512))  # path within the corpus
    title: Mapped[str] = mapped_column(String(512))
    url: Mapped[str | None] = mapped_column(String(1024))  # public URL for attribution
    content_hash: Mapped[str] = mapped_column(String(64))
    status: Mapped[DocumentStatus] = mapped_column(
        str_enum(DocumentStatus), default=DocumentStatus.PENDING
    )
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    last_indexed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error: Mapped[str | None] = mapped_column(Text)

    chunks: Mapped[list["KnowledgeChunk"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )


class KnowledgeChunk(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    """A retrievable piece of a document, with its embedding.

    Full-text search runs over `content` via an expression GIN index (created
    in the migration); vector search over `embedding` via HNSW.
    """

    __tablename__ = "knowledge_chunks"
    __table_args__ = (UniqueConstraint("document_id", "chunk_index"),)

    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("knowledge_documents.id", ondelete="CASCADE"), index=True
    )
    chunk_index: Mapped[int] = mapped_column(Integer)
    heading: Mapped[str | None] = mapped_column(String(512))
    content: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM))

    document: Mapped[KnowledgeDocument] = relationship(back_populates="chunks")


class RetrievalEvent(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    """Audit log of every retrieval: what was asked, what came back, how fast.

    Linked to a conversation when the agent searched mid-call; null for
    dashboard/API searches. This is what powers 'evidence' in the replay view
    and the retrieval metrics in evaluations.
    """

    __tablename__ = "retrieval_events"

    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("conversations.id"), index=True
    )
    query: Mapped[str] = mapped_column(Text)
    strategy: Mapped[str] = mapped_column(String(32))  # e.g. "hybrid_rrf"
    top_k: Mapped[int] = mapped_column(Integer)
    results: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    latency_ms: Mapped[int] = mapped_column(Integer)
