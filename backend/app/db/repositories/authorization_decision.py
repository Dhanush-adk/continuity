import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.authorization_decision import AuthorizationDecision


def get(db: Session, authorization_decision_id: uuid.UUID) -> AuthorizationDecision | None:
    return db.scalar(
        select(AuthorizationDecision).where(AuthorizationDecision.id == authorization_decision_id)
    )


def list_recent(
    db: Session, *, organization_id: uuid.UUID | None = None, limit: int = 50
) -> list[AuthorizationDecision]:
    statement = (
        select(AuthorizationDecision).order_by(AuthorizationDecision.created_at.desc()).limit(limit)
    )
    if organization_id is not None:
        statement = statement.where(AuthorizationDecision.organization_id == organization_id)
    return list(db.scalars(statement))


def add(db: Session, authorization_decision: AuthorizationDecision) -> AuthorizationDecision:
    db.add(authorization_decision)
    db.commit()
    db.refresh(authorization_decision)
    return authorization_decision
