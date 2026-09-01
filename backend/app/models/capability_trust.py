import uuid
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Boolean, DateTime, Enum, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.agent_version import AgentVersion


class CapabilityTrustStatus(StrEnum):
    TRUSTED = "TRUSTED"
    LIMITED = "LIMITED"
    UNTRUSTED = "UNTRUSTED"


class ContinuityAction(StrEnum):
    INHERIT = "INHERIT"
    RESTRICT = "RESTRICT"
    REAUTHORIZE = "REAUTHORIZE"


class CapabilityTrust(Base):
    __tablename__ = "capability_trusts"
    __table_args__ = (UniqueConstraint("agent_version_id", "capability_name"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    agent_version_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agent_versions.id"), index=True)
    capability_name: Mapped[str] = mapped_column(String(255))
    status: Mapped[CapabilityTrustStatus] = mapped_column(Enum(CapabilityTrustStatus))
    continuity_action: Mapped[ContinuityAction] = mapped_column(Enum(ContinuityAction))
    inherited_from_version_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True)
    autonomy_constraints: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    reason_codes: Mapped[list[str]] = mapped_column(JSON, default=list)
    explicitly_reauthorized: Mapped[bool] = mapped_column(Boolean, default=False)
    reauthorized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reauthorization_reason: Mapped[str | None] = mapped_column(String(1_000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    agent_version: Mapped["AgentVersion"] = relationship(back_populates="capability_trusts")
