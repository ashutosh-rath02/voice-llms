import enum
import uuid
from typing import Any

from sqlalchemy import ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtMixin, TimestampMixin, UUIDPrimaryKeyMixin, str_enum


class ToolExecutionStatus(enum.StrEnum):
    PROPOSED = "proposed"
    EXECUTING = "executing"
    SUCCEEDED = "succeeded"
    REJECTED = "rejected"


class ToolExecution(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """One consequential action the agent proposed, from proposal to outcome.

    No separate idempotency-key column: `id` (this row) IS the idempotency
    key. Executing is guarded by an atomic `UPDATE ... WHERE status =
    'proposed'` (see agent/confirmation.py) — only the caller that wins that
    conditional update actually runs the side effect, so a repeated
    confirm_pending_action call for the same id can never double-execute.
    On an unhandled executor error the whole transaction rolls back, which
    reverts status to 'proposed' rather than stranding a 'failed' row —
    the same confirmation can safely be retried without re-asking the user.
    """

    __tablename__ = "tool_executions"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("conversations.id"), index=True
    )
    tool_name: Mapped[str] = mapped_column(Text)  # dispatch key into EXECUTORS
    arguments: Mapped[dict[str, Any]] = mapped_column(JSONB)
    status: Mapped[ToolExecutionStatus] = mapped_column(
        str_enum(ToolExecutionStatus), default=ToolExecutionStatus.PROPOSED
    )
    result: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    confirmation: Mapped["ToolConfirmation | None"] = relationship(
        back_populates="tool_execution", cascade="all, delete-orphan"
    )


class ToolConfirmation(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    """Audit record: the caller explicitly confirmed this action.

    Existence of this row is the record required by PRD 6.9 ("confirmation
    must be stored") — one per execution, written atomically alongside the
    proposed->executing transition.
    """

    __tablename__ = "tool_confirmations"

    tool_execution_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tool_executions.id", ondelete="CASCADE"), unique=True
    )

    tool_execution: Mapped[ToolExecution] = relationship(back_populates="confirmation")
