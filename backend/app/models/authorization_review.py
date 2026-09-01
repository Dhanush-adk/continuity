import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class HumanReviewDecision(StrEnum):
    APPROVE = "APPROVE"
    DENY = "DENY"


class AuthorizationReview(Base):
    """An immutable human disposition of a prior REVIEW authorization outcome."""

    __tablename__ = "authorization_reviews"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    authorization_decision_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("authorization_decisions.id"), unique=True, index=True
    )
    decision: Mapped[HumanReviewDecision] = mapped_column(
        Enum(HumanReviewDecision, name="human_review_decision")
    )
    reviewer_id: Mapped[str] = mapped_column(String(255))
    reviewer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reason: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
