import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.repositories import agent as agent_repository
from app.db.session import get_db
from app.schemas.agent import AgentRead
from app.schemas.organization import OrganizationCreate, OrganizationRead
from app.services import organization as organizations

router = APIRouter(prefix="/organizations", tags=["organizations"])


@router.post("", response_model=OrganizationRead, status_code=status.HTTP_201_CREATED)
def create_organization(
    payload: OrganizationCreate, db: Session = Depends(get_db)
) -> OrganizationRead:
    try:
        return organizations.create(db, payload)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Organization name already exists") from exc


@router.get("", response_model=list[OrganizationRead])
def list_organizations(db: Session = Depends(get_db)) -> list[OrganizationRead]:
    return organizations.list_all(db)


@router.get("/{organization_id}/agents", response_model=list[AgentRead])
def list_agents(organization_id: uuid.UUID, db: Session = Depends(get_db)) -> list[AgentRead]:
    if organizations.get(db, organization_id) is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    return agent_repository.list_for_organization(db, organization_id)
