import uuid

from sqlalchemy.orm import Session

from app.db.repositories import organization as organizations
from app.models.organization import Organization
from app.schemas.organization import OrganizationCreate


def create(db: Session, payload: OrganizationCreate) -> Organization:
    return organizations.add(db, Organization(name=payload.name))


def list_all(db: Session) -> list[Organization]:
    return organizations.list_all(db)


def get(db: Session, organization_id: uuid.UUID) -> Organization | None:
    return organizations.get(db, organization_id)
