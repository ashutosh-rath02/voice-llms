import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class RoleName(enum.StrEnum):
    """RBAC roles from the PRD (§5): who may see and do what."""

    ADMIN = "admin"  # platform engineer: providers, deployments, evals
    SUPPORT_MANAGER = "support_manager"  # metrics, policies, review
    SUPPORT_AGENT = "support_agent"  # live calls, takeover, tickets
    CUSTOMER = "customer"  # own conversations only


class Role(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "roles"

    name: Mapped[str] = mapped_column(String(32), unique=True)
    description: Mapped[str | None] = mapped_column(String(255))

    users: Mapped[list["User"]] = relationship(back_populates="role")


class User(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A person who can log in: customers, support staff, admins.

    Callers identified only by phone number (Phase 4) become `customers`
    records, a separate table — a customer does not need a login to call.
    """

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(255))
    role_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("roles.id"))
    is_active: Mapped[bool] = mapped_column(default=True)
    # Soft delete: rows are retained for audit/traceability and excluded by
    # queries; the PRD's deletion workflow decides when rows are truly purged.
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    role: Mapped[Role] = relationship(back_populates="users")
