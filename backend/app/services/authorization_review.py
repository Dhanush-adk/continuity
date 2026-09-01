import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.repositories import authorization_decision as decisions
from app.db.repositories import authorization_review as reviews
from app.models.authorization_decision import AuthorizationDecision, AuthorizationOutcome
from app.models.authorization_review import AuthorizationReview
from app.schemas.authorization import AuthorizationDecisionRead
from app.schemas.authorization_review import AuthorizationReviewCreate, AuthorizationReviewRead


class AuthorizationReviewNotFoundError(ValueError):
    pass


class AuthorizationReviewConflictError(ValueError):
    pass


def _read(
    decision: AuthorizationDecision, review: AuthorizationReview | None
) -> AuthorizationDecisionRead:
    return AuthorizationDecisionRead.model_validate(
        {
            "id": decision.id,
            "organization_id": decision.organization_id,
            "agent_id": decision.agent_id,
            "agent_version_id": decision.agent_version_id,
            "mandate_id": decision.mandate_id,
            "capability_name": decision.capability_name,
            "decision": decision.decision,
            "reason_codes": decision.reason_codes,
            "proposed_action": decision.proposed_action,
            "capability_trust_snapshot": decision.capability_trust_snapshot,
            "mandate_snapshot": decision.mandate_snapshot,
            "policy_snapshot": decision.policy_snapshot,
            "created_at": decision.created_at,
            "review": review,
        }
    )


def get(db: Session, authorization_decision_id: uuid.UUID) -> AuthorizationDecisionRead:
    decision = decisions.get(db, authorization_decision_id)
    if decision is None:
        raise AuthorizationReviewNotFoundError("Authorization decision not found")
    return _read(decision, reviews.get_for_decision(db, decision.id))


def list_recent(
    db: Session, *, organization_id: uuid.UUID | None = None, limit: int = 50
) -> list[AuthorizationDecisionRead]:
    return [
        _read(decision, reviews.get_for_decision(db, decision.id))
        for decision in decisions.list_recent(db, organization_id=organization_id, limit=limit)
    ]


def create(
    db: Session, authorization_decision_id: uuid.UUID, payload: AuthorizationReviewCreate
) -> AuthorizationReviewRead:
    decision = decisions.get(db, authorization_decision_id)
    if decision is None:
        raise AuthorizationReviewNotFoundError("Authorization decision not found")
    if decision.decision != AuthorizationOutcome.REVIEW:
        raise AuthorizationReviewConflictError(
            "Only REVIEW authorizations can receive a human review"
        )
    if reviews.get_for_decision(db, authorization_decision_id) is not None:
        raise AuthorizationReviewConflictError("Authorization already has a human review")
    try:
        review = reviews.add(
            db,
            AuthorizationReview(
                authorization_decision_id=authorization_decision_id,
                decision=payload.decision,
                reviewer_id=payload.reviewer_id,
                reviewer_name=payload.reviewer_name,
                reason=payload.reason,
            ),
        )
    except IntegrityError as exc:
        db.rollback()
        raise AuthorizationReviewConflictError("Authorization already has a human review") from exc
    return AuthorizationReviewRead.model_validate(review)
