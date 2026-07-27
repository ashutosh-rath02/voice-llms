"""Generic propose -> confirm/reject infrastructure every write tool plugs into.

Implements PRD 6.5's ACTION_PROPOSAL -> USER_CONFIRMATION -> TOOL_EXECUTION
flow and 6.9's confirmation requirements. The state machine is deliberately
generic — the LLM-facing tool wrappers in agent/tools.py are thin, and the
actual side effect for a given `tool_name` is looked up here in EXECUTORS,
never chosen by the model itself. That indirection is a safety property: the
LLM can request an action by name, but cannot smuggle in arbitrary code to run.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

import structlog
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ToolConfirmation, ToolExecution, ToolExecutionStatus

if TYPE_CHECKING:
    # Type-only: tools.py imports propose/confirm/reject from this module, so
    # importing SessionData from tools.py at runtime would be circular.
    from app.agent.tools import SessionData

log = structlog.get_logger()

Executor = Callable[[AsyncSession, dict[str, Any]], Awaitable[dict[str, Any]]]

EXECUTORS: dict[str, Executor] = {}


def register_executor(tool_name: str, fn: Executor) -> None:
    """Wire a real action into the confirm step. Called at import time by the
    module that owns that action (e.g. services/customers.py)."""
    EXECUTORS[tool_name] = fn


async def propose_tool_execution(
    data: SessionData, tool_name: str, arguments: dict[str, Any]
) -> ToolExecution:
    """ACTION_PROPOSAL: record intent. No side effect runs yet."""
    async with data.db_sessions() as session:
        execution = ToolExecution(
            conversation_id=data.conversation_id,
            tool_name=tool_name,
            arguments=arguments,
            status=ToolExecutionStatus.PROPOSED,
        )
        session.add(execution)
        await session.commit()
        await session.refresh(execution)
        log.info("tool_execution_proposed", id=str(execution.id), tool_name=tool_name)
        return execution


async def confirm_tool_execution(data: SessionData, execution_id: str) -> str:
    """USER_CONFIRMATION -> TOOL_EXECUTION.

    The `WHERE status = 'proposed'` update is the whole idempotency
    mechanism: exactly one caller can ever win it for a given execution_id.
    A repeated confirm (duplicate tool call, user saying yes twice) always
    loses the race the second time and returns the already-settled outcome
    instead of running the side effect again.
    """
    async with data.db_sessions() as session:
        execution = await session.get(ToolExecution, execution_id)
        if execution is None or str(execution.conversation_id) != data.conversation_id:
            return "I don't have a pending action with that reference."
        if execution.status != ToolExecutionStatus.PROPOSED:
            return _settled_message(execution)

        cas = await session.execute(
            update(ToolExecution)
            .where(
                ToolExecution.id == execution.id,
                ToolExecution.status == ToolExecutionStatus.PROPOSED,
            )
            .values(status=ToolExecutionStatus.EXECUTING)
        )
        if cas.rowcount == 0:
            return "That action was already handled a moment ago."

        session.add(ToolConfirmation(tool_execution_id=execution.id))

        executor = EXECUTORS.get(execution.tool_name)
        if executor is None:
            # Log before rollback: rollback expires `execution`, and reading
            # an expired attribute triggers an async lazy-load that isn't
            # valid outside an awaited context (SQLAlchemy MissingGreenlet).
            log.error("no_executor_registered", tool_name=execution.tool_name)
            await session.rollback()
            return "I can't complete that action right now — please try again later."

        try:
            result = await executor(session, execution.arguments)
        except Exception:
            # Roll back everything, including the EXECUTING transition — the
            # row reverts to 'proposed', so the same confirmation can be
            # retried without re-asking the caller for a fresh yes.
            log.exception(
                "tool_execution_failed", id=str(execution.id), tool_name=execution.tool_name
            )
            await session.rollback()
            return "I ran into a problem completing that. Want me to try again?"

        execution.status = ToolExecutionStatus.SUCCEEDED
        execution.result = result
        await session.commit()
        log.info("tool_execution_succeeded", id=str(execution.id), tool_name=execution.tool_name)
        return str(result.get("summary", "Done."))


async def reject_tool_execution(data: SessionData, execution_id: str) -> str:
    """The caller declined or changed their mind before confirming."""
    async with data.db_sessions() as session:
        result = await session.execute(
            update(ToolExecution)
            .where(
                ToolExecution.id == execution_id,
                ToolExecution.conversation_id == data.conversation_id,
                ToolExecution.status == ToolExecutionStatus.PROPOSED,
            )
            .values(status=ToolExecutionStatus.REJECTED)
        )
        await session.commit()
        if result.rowcount == 0:
            return "There's no pending action to cancel."
        return "Okay, I won't do that."


def _settled_message(execution: ToolExecution) -> str:
    if execution.status == ToolExecutionStatus.SUCCEEDED:
        summary = (execution.result or {}).get("summary", "already completed")
        return f"That was already done: {summary}"
    if execution.status == ToolExecutionStatus.REJECTED:
        return "That action was already cancelled."
    return "That action is currently in progress."
