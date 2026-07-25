"""All ORM models. Importing this package registers every table on
Base.metadata — which is exactly what Alembic autogenerate diffs against."""

from app.models.agent import AgentVersion, AgentVersionStatus, ProviderConfig
from app.models.base import Base
from app.models.conversation import (
    AgentState,
    AgentStateEvent,
    Conversation,
    ConversationChannel,
    ConversationStatus,
    ConversationTurn,
    TurnLatencyMetric,
    TurnRole,
)
from app.models.user import Role, RoleName, User

__all__ = [
    "AgentState",
    "AgentStateEvent",
    "AgentVersion",
    "AgentVersionStatus",
    "Base",
    "Conversation",
    "ConversationChannel",
    "ConversationStatus",
    "ConversationTurn",
    "ProviderConfig",
    "Role",
    "RoleName",
    "TurnLatencyMetric",
    "TurnRole",
    "User",
]
