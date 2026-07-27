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
from app.models.customer import (
    ContactType,
    Customer,
    CustomerContact,
    CustomerProduct,
    CustomerProductStatus,
    ProductOrService,
)
from app.models.knowledge import (
    EMBEDDING_DIM,
    DocumentStatus,
    KnowledgeChunk,
    KnowledgeDocument,
    RetrievalEvent,
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
    "ContactType",
    "Customer",
    "CustomerContact",
    "CustomerProduct",
    "CustomerProductStatus",
    "DocumentStatus",
    "EMBEDDING_DIM",
    "KnowledgeChunk",
    "KnowledgeDocument",
    "ProductOrService",
    "ProviderConfig",
    "RetrievalEvent",
    "Role",
    "RoleName",
    "TurnLatencyMetric",
    "TurnRole",
    "User",
]
