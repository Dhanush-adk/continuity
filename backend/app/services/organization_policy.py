import uuid

from sqlalchemy.orm import Session

from app.db.repositories import organization_policy as policies
from app.models.organization_policy import OrganizationPolicy
from app.schemas.organization_policy import OrganizationPolicyUpsert


def get(db: Session, organization_id: uuid.UUID) -> OrganizationPolicy | None:
    return policies.get_for_organization(db, organization_id)


def upsert(
    db: Session, organization_id: uuid.UUID, payload: OrganizationPolicyUpsert
) -> OrganizationPolicy:
    policy = policies.get_for_organization(db, organization_id)
    if policy is None:
        policy = OrganizationPolicy(organization_id=organization_id)
    values = payload.model_dump()
    policy.approved_vendors = values["approved_vendors"]
    policy.approval_thresholds = values["approval_thresholds"]
    policy.hard_payment_limit = values["hard_payment_limit"]
    return policies.save(db, policy)
