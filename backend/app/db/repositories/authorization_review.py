import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.authorization_review import AuthorizationReview


def get_for_decision(
    db: Session, authorization_decision_id: uuid.UUID
) -> AuthorizationReview | None:
    return db.scalar(
        select(AuthorizationReview).where(
            AuthorizationReview.authorization_decision_id == authorization_decision_id
        )
    )


def add(db: Session, review: AuthorizationReview) -> AuthorizationReview:
    db.add(review)
    db.commit()
    db.refresh(review)
    return review
