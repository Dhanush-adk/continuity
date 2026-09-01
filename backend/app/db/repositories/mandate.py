import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.mandate import Mandate


def get(db: Session, mandate_id: uuid.UUID) -> Mandate | None:
    return db.scalar(select(Mandate).where(Mandate.id == mandate_id))


def save(db: Session, mandate: Mandate) -> Mandate:
    db.add(mandate)
    db.commit()
    db.refresh(mandate)
    return mandate
