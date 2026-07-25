import uuid

import structlog
from fastapi import APIRouter, HTTPException, Request, status
from livekit import api as lk_api
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.models import (
    AgentVersion,
    AgentVersionStatus,
    Conversation,
    ConversationChannel,
)
from app.schemas.voice import VoiceSessionOut

router = APIRouter(prefix="/voice", tags=["voice"])
log = structlog.get_logger()


@router.post("/token", response_model=VoiceSessionOut)
async def create_voice_session(
    request: Request, user: CurrentUser, session: DbSession
) -> VoiceSessionOut:
    """Create a conversation row and mint a room-scoped LiveKit join token.

    The conversation row is created *before* the user joins, so the agent
    worker can look it up by room name the moment it is dispatched — the
    room name is the join key between the two processes.
    """
    settings = request.app.state.settings
    if not (settings.livekit_url and settings.livekit_api_key and settings.livekit_api_secret):
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "Voice infrastructure is not configured"
        )

    agent_version = (
        await session.execute(
            select(AgentVersion)
            .where(AgentVersion.status == AgentVersionStatus.ACTIVE)
            .order_by(AgentVersion.created_at.desc())
        )
    ).scalars().first()
    if agent_version is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "No active agent version")

    room_name = f"voice-{uuid.uuid4().hex}"
    conversation = Conversation(
        user_id=user.id,
        agent_version_id=agent_version.id,
        channel=ConversationChannel.BROWSER,
        room_name=room_name,
    )
    session.add(conversation)
    await session.commit()

    token = (
        lk_api.AccessToken(settings.livekit_api_key, settings.livekit_api_secret)
        .with_identity(str(user.id))
        .with_name(user.full_name)
        .with_grants(lk_api.VideoGrants(room_join=True, room=room_name))
        .to_jwt()
    )
    log.info(
        "voice_session_created",
        conversation_id=str(conversation.id),
        room=room_name,
        agent_version=agent_version.version_label,
    )
    return VoiceSessionOut(
        token=token,
        url=settings.livekit_url,
        room_name=room_name,
        conversation_id=conversation.id,
    )
