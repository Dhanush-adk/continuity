import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AuthorizationOutcome(StrEnum):
    ALLOW = "ALLOW"
    REVIEW = "REVIEW"
    DENY = "DENY"


class AuthorizationDecision(Base):
    __tablename__ = "authorization_decisions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    agent_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agents.id"), index=True)
    agent_version_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agent_versions.id"), index=True)
    mandate_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("mandates.id"), index=True)
    capability_name: Mapped[str] = mapped_column(String(255))
    proposed_action: Mapped[dict[str, Any]] = mapped_column(JSON)
    decision: Mapped[AuthorizationOutcome] = mapped_column(
        Enum(AuthorizationOutcome, name="authorization_outcome")
    )
    reason_codes: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    capability_trust_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON)
    mandate_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON)
    policy_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
