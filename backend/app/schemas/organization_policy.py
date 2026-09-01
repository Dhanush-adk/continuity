import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ApprovalThreshold(BaseModel):
    amount_gte: int = Field(ge=0)
    action: Literal["REVIEW"] = "REVIEW"


class OrganizationPolicyUpsert(BaseModel):
    approved_vendors: list[str] = Field(default_factory=list)
    approval_thresholds: list[ApprovalThreshold] = Field(default_factory=list)
    hard_payment_limit: int | None = Field(default=None, ge=0)

    @field_validator("approved_vendors")
    @classmethod
    def vendors_must_be_unique(cls, vendors: list[str]) -> list[str]:
        if len(vendors) != len(set(vendors)):
            raise ValueError("approved_vendors must not contain duplicates")
        return vendors


class OrganizationPolicyRead(OrganizationPolicyUpsert):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
