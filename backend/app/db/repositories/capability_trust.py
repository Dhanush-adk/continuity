import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.capability_trust import CapabilityTrust


def get_for_version(
    db: Session, agent_version_id: uuid.UUID, capability_name: str
) -> CapabilityTrust | None:
    return db.scalar(
        select(CapabilityTrust).where(
            CapabilityTrust.agent_version_id == agent_version_id,
            CapabilityTrust.capability_name == capability_name,
        )
    )


def list_for_version(db: Session, agent_version_id: uuid.UUID) -> list[CapabilityTrust]:
    statement = select(CapabilityTrust).where(CapabilityTrust.agent_version_id == agent_version_id)
    return list(db.scalars(statement))


def save(db: Session, trust: CapabilityTrust) -> CapabilityTrust:
    db.add(trust)
    db.commit()
    db.refresh(trust)
    return trust
