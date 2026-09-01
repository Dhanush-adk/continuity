import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class MandateStatus(StrEnum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"


class Mandate(Base):
    __tablename__ = "mandates"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    requester_id: Mapped[str] = mapped_column(String(255))
    agent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("agents.id"), nullable=True, index=True
    )
    raw_intent: Mapped[str] = mapped_column(Text)
    raw_extraction: Mapped[dict[str, Any]] = mapped_column(JSON)
    structured_intent: Mapped[dict[str, Any]] = mapped_column(JSON)
    canonicalization_issues: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    status: Mapped[MandateStatus] = mapped_column(Enum(MandateStatus, name="mandate_status"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
