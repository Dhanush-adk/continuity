import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.organization import Organization


def add(db: Session, organization: Organization) -> Organization:
    db.add(organization)
    db.commit()
    db.refresh(organization)
    return organization


def get(db: Session, organization_id: uuid.UUID) -> Organization | None:
    return db.scalar(select(Organization).where(Organization.id == organization_id))


def get_by_name(db: Session, name: str) -> Organization | None:
    return db.scalar(select(Organization).where(Organization.name == name))


def list_all(db: Session) -> list[Organization]:
    return list(db.scalars(select(Organization).order_by(Organization.created_at)))
