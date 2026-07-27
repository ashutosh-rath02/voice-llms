import uuid

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DbSession
from app.models import AgentVersion, Conversation, ConversationTurn, RetrievalEvent, RoleName
from app.schemas.conversations import (
    ConversationDetail,
    ConversationSummary,
    RetrievalEventOut,
    StateEventOut,
    TurnOut,
)

router = APIRouter(prefix="/conversations", tags=["conversations"])

STAFF_ROLES = (RoleName.ADMIN, RoleName.SUPPORT_AGENT, RoleName.SUPPORT_MANAGER)


def _is_staff(user) -> bool:
    return user.role.name in STAFF_ROLES


@router.get("", response_model=list[ConversationSummary])
async def list_conversations(
    user: CurrentUser,
    session: DbSession,
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
) -> list[Conversation]:
    """Customers see their own sessions; staff see everything (including
    ad-hoc test rooms that have no user attached)."""
    query = (
        select(Conversation)
        .where(Conversation.deleted_at.is_(None))
        .order_by(Conversation.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    if not _is_staff(user):
        query = query.where(Conversation.user_id == user.id)
    return list((await session.execute(query)).scalars().all())


@router.get("/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(
    conversation_id: uuid.UUID, user: CurrentUser, session: DbSession
) -> ConversationDetail:
    conversation = (
        await session.execute(
            select(Conversation)
            .options(
                selectinload(Conversation.turns).selectinload(ConversationTurn.latency),
                selectinload(Conversation.state_events),
            )
            .where(Conversation.id == conversation_id, Conversation.deleted_at.is_(None))
        )
    ).scalar_one_or_none()
    if conversation is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")
    if not _is_staff(user) and conversation.user_id != user.id:
        # 404, not 403: don't confirm to a customer that someone else's
        # conversation id exists.
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")

    agent_version_label = (
        await session.execute(
            select(AgentVersion.version_label).where(
                AgentVersion.id == conversation.agent_version_id
            )
        )
    ).scalar_one()

    retrieval_events = (
        await session.execute(
            select(RetrievalEvent)
            .where(RetrievalEvent.conversation_id == conversation.id)
            .order_by(RetrievalEvent.created_at)
        )
    ).scalars().all()

    return ConversationDetail(
        **ConversationSummary.model_validate(conversation).model_dump(),
        agent_version_label=agent_version_label,
        turns=[
            TurnOut(
                turn_index=t.turn_index,
                role=t.role,
                content=t.content,
                language=t.language,
                interrupted=t.interrupted,
                created_at=t.created_at,
                latency=t.latency,
                partials=(t.extra or {}).get("partials", []),
            )
            for t in conversation.turns
        ],
        state_events=[StateEventOut.model_validate(e) for e in conversation.state_events],
        retrieval_events=[
            RetrievalEventOut(
                query=e.query,
                strategy=e.strategy,
                latency_ms=e.latency_ms,
                created_at=e.created_at,
                results=e.results,
            )
            for e in retrieval_events
        ],
    )
