import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.agent import Agent
    from app.models.capability_trust import CapabilityTrust


class AgentVersion(Base):
    __tablename__ = "agent_versions"
    __table_args__ = (UniqueConstraint("agent_id", "version"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agents.id"), index=True)
    version: Mapped[str] = mapped_column(String(100))
    model_name: Mapped[str] = mapped_column(String(255))
    prompt_hash: Mapped[str] = mapped_column(String(128))
    code_hash: Mapped[str] = mapped_column(String(128))
    tool_manifest: Mapped[dict[str, Any] | list[Any]] = mapped_column(JSON)
    capability_manifest: Mapped[dict[str, Any] | list[Any]] = mapped_column(JSON)
    permissions: Mapped[dict[str, Any] | list[Any]] = mapped_column(JSON)
    deployment_fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    agent: Mapped["Agent"] = relationship(back_populates="versions")
    capability_trusts: Mapped[list["CapabilityTrust"]] = relationship(
        back_populates="agent_version", cascade="all, delete-orphan"
    )
