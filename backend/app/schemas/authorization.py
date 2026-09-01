import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.authorization_decision import AuthorizationOutcome
from app.schemas.authorization_review import AuthorizationReviewRead


class ProposedProcurementAction(BaseModel):
    action_type: str
    item_category: str
    quantity: int = Field(ge=1)
    amount: int = Field(ge=0)
    currency: str = Field(min_length=3, max_length=3)
    vendor: str = Field(min_length=1, max_length=255)
    purpose: str | None = None


class AuthorizationRequest(BaseModel):
    organization_id: uuid.UUID
    agent_id: uuid.UUID
    agent_version_id: uuid.UUID
    capability: str = Field(min_length=1, max_length=255)
    mandate_id: uuid.UUID
    action: ProposedProcurementAction


class ReasonDetail(BaseModel):
    code: str
    expected: Any | None = None
    actual: Any | None = None


class AuthorizationCheck(BaseModel):
    status: Literal["PASS", "REVIEW", "FAIL"]
    trust_status: str | None = None
    trusted_envelope: dict[str, Any] | None = None


class AuthorizationChecks(BaseModel):
    deployment: AuthorizationCheck
    capability: AuthorizationCheck
    mandate: AuthorizationCheck
    organization_policy: AuthorizationCheck


class AuthorizationResponse(BaseModel):
    decision_id: uuid.UUID
    decision: AuthorizationOutcome
    checks: AuthorizationChecks
    reasons: list[ReasonDetail]
    created_at: datetime


class AuthorizationDecisionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    agent_id: uuid.UUID
    agent_version_id: uuid.UUID
    mandate_id: uuid.UUID
    capability_name: str
    decision: AuthorizationOutcome
    reason_codes: list[dict[str, Any]]
    proposed_action: dict[str, Any]
    capability_trust_snapshot: dict[str, Any]
    mandate_snapshot: dict[str, Any]
    policy_snapshot: dict[str, Any]
    created_at: datetime
    review: AuthorizationReviewRead | None = None
