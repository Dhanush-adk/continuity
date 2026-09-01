import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.capability_trust import CapabilityTrustStatus, ContinuityAction
from app.services.change_classifier import ChangeSeverity


class ContinuityEvaluationRequest(BaseModel):
    previous_version_id: uuid.UUID


class ReauthorizationRequest(BaseModel):
    autonomy_constraints: dict[str, Any]
    reason: str = Field(min_length=1, max_length=1_000)


class CapabilityTrustRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    agent_version_id: uuid.UUID
    capability_name: str
    status: CapabilityTrustStatus
    continuity_action: ContinuityAction
    inherited_from_version_id: uuid.UUID | None
    autonomy_constraints: dict[str, Any]
    reason_codes: list[str]
    explicitly_reauthorized: bool
    reauthorized_at: datetime | None
    reauthorization_reason: str | None
    created_at: datetime


class CapabilityContinuityResult(BaseModel):
    capability_name: str
    decision: ContinuityAction
    resulting_status: CapabilityTrustStatus
    change_severity: ChangeSeverity
    inherited_from_version_id: uuid.UUID | None
    autonomy_constraints: dict[str, Any]
    reasons: list[str]
    explicitly_reauthorized: bool


class ContinuitySummary(BaseModel):
    inherited: int
    restricted: int
    reauthorization_required: int


class ContinuityEvaluationResponse(BaseModel):
    agent_id: uuid.UUID
    from_version: str
    to_version: str
    summary: ContinuitySummary
    capabilities: list[CapabilityContinuityResult]
