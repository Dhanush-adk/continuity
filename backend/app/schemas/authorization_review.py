import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.authorization_review import HumanReviewDecision


class AuthorizationReviewCreate(BaseModel):
    decision: HumanReviewDecision
    reviewer_id: str = Field(min_length=1, max_length=255)
    reviewer_name: str | None = Field(default=None, max_length=255)
    reason: str = Field(min_length=1, max_length=2_000)


class AuthorizationReviewRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    authorization_decision_id: uuid.UUID
    decision: HumanReviewDecision
    reviewer_id: str
    reviewer_name: str | None
    reason: str
    created_at: datetime
