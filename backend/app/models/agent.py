import enum
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, str_enum


class AgentVersionStatus(enum.StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    INACTIVE = "inactive"
    ROLLED_BACK = "rolled_back"


class AgentVersion(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A deployable agent configuration: prompt + model/provider choices.

    Every conversation records which version served it, which is what makes
    version-vs-version evaluation comparison (PRD §6.12, §8) possible.
    Versions are immutable once conversations reference them — behaviour
    changes mean a new row, not an edit.
    """

    __tablename__ = "agent_versions"

    version_label: Mapped[str] = mapped_column(String(64), unique=True)
    status: Mapped[AgentVersionStatus] = mapped_column(
        str_enum(AgentVersionStatus), default=AgentVersionStatus.DRAFT
    )
    system_prompt: Mapped[str] = mapped_column(Text)

    llm_provider: Mapped[str] = mapped_column(String(64))
    llm_model: Mapped[str] = mapped_column(String(128))
    stt_provider: Mapped[str] = mapped_column(String(64))
    stt_model: Mapped[str] = mapped_column(String(128))
    tts_provider: Mapped[str] = mapped_column(String(64))
    tts_model: Mapped[str] = mapped_column(String(128))
    tts_voice: Mapped[str] = mapped_column(String(128))

    # Free-form knobs (temperature, endpointing overrides…) that shouldn't
    # each need a schema migration.
    config: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    deployed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ProviderConfig(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Named runtime tuning bundles (e.g. turn-detection thresholds).

    Kept in the database, not code, so operators can tune behaviour per the
    PRD ("configurable endpointing") without a redeploy.
    """

    __tablename__ = "provider_configs"

    name: Mapped[str] = mapped_column(String(128), unique=True)
    description: Mapped[str | None] = mapped_column(String(255))
    config: Mapped[dict[str, Any]] = mapped_column(JSONB)
    is_active: Mapped[bool] = mapped_column(default=True)
