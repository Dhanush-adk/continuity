import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.repositories import agent as agents
from app.db.repositories import organization as organizations
from app.db.session import get_db
from app.schemas.mandate import MandateExtractRequest, MandateRead
from app.services import mandate as mandates
from app.services.intent_extractor import IntentExtractor, get_intent_extractor

router = APIRouter(prefix="/mandates", tags=["mandates"])


@router.post("/extract", response_model=MandateRead, status_code=status.HTTP_201_CREATED)
def extract_mandate(
    payload: MandateExtractRequest,
    db: Session = Depends(get_db),
    extractor: IntentExtractor = Depends(get_intent_extractor),
) -> MandateRead:
    if organizations.get(db, payload.organization_id) is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    if payload.agent_id is not None:
        agent = agents.get(db, payload.agent_id)
        if agent is None or agent.organization_id != payload.organization_id:
            raise HTTPException(status_code=404, detail="Agent not found")
    try:
        return mandates.extract_and_create(db, payload, extractor)
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/{mandate_id}/activate", response_model=MandateRead)
def activate_mandate(mandate_id: uuid.UUID, db: Session = Depends(get_db)) -> MandateRead:
    mandate = mandates.get(db, mandate_id)
    if mandate is None:
        raise HTTPException(status_code=404, detail="Mandate not found")
    try:
        return mandates.activate(db, mandate)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
