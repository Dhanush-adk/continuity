import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.organization_policy import OrganizationPolicy


def get_for_organization(db: Session, organization_id: uuid.UUID) -> OrganizationPolicy | None:
    return db.scalar(
        select(OrganizationPolicy).where(OrganizationPolicy.organization_id == organization_id)
    )


def save(db: Session, policy: OrganizationPolicy) -> OrganizationPolicy:
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return policy
