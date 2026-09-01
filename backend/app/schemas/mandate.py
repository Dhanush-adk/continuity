import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.mandate import MandateStatus


class ProcurementIntent(BaseModel):
    action_type: str | None = None
    item_category: str | None = None
    quantity_max: int | None = Field(default=None, ge=1)
    max_amount: int | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    vendor_policy: Literal["approved_only", "any", "unspecified"] = "unspecified"
    approved_vendors: list[str] | None = None
    purpose: str | None = None


class CanonicalizationIssue(BaseModel):
    field: str
    code: str
    value: Any


class MandateExtractRequest(BaseModel):
    organization_id: uuid.UUID
    requester_id: str = Field(min_length=1, max_length=255)
    agent_id: uuid.UUID | None = None
    text: str = Field(min_length=1, max_length=10_000)
    expires_at: datetime | None = None


class MandateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    requester_id: str
    agent_id: uuid.UUID | None
    raw_intent: str
    raw_extraction: ProcurementIntent
    structured_intent: ProcurementIntent
    canonicalization_issues: list[CanonicalizationIssue]
    status: MandateStatus
    created_at: datetime
    expires_at: datetime | None
