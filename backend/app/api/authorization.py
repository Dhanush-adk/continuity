import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.authorization import (
    AuthorizationDecisionRead,
    AuthorizationRequest,
    AuthorizationResponse,
)
from app.schemas.authorization_review import AuthorizationReviewCreate, AuthorizationReviewRead
from app.services import authorization, authorization_review

router = APIRouter(tags=["authorization"])


@router.post("/authorize", response_model=AuthorizationResponse)
def authorize_action(
    payload: AuthorizationRequest, db: Session = Depends(get_db)
) -> AuthorizationResponse:
    try:
        return authorization.authorize(db, payload)
    except authorization.AuthorizationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/authorizations", response_model=list[AuthorizationDecisionRead])
def list_authorizations(
    organization_id: uuid.UUID | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> list[AuthorizationDecisionRead]:
    return authorization_review.list_recent(db, organization_id=organization_id, limit=limit)


@router.get("/authorizations/{authorization_id}", response_model=AuthorizationDecisionRead)
def get_authorization(
    authorization_id: uuid.UUID, db: Session = Depends(get_db)
) -> AuthorizationDecisionRead:
    try:
        return authorization_review.get(db, authorization_id)
    except authorization_review.AuthorizationReviewNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/authorizations/{authorization_id}/review",
    response_model=AuthorizationReviewRead,
    status_code=201,
)
def review_authorization(
    authorization_id: uuid.UUID,
    payload: AuthorizationReviewCreate,
    db: Session = Depends(get_db),
) -> AuthorizationReviewRead:
    try:
        return authorization_review.create(db, authorization_id, payload)
    except authorization_review.AuthorizationReviewNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except authorization_review.AuthorizationReviewConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
