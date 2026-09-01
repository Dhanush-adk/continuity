import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.repositories import capability_trust as capability_trust_repository
from app.db.repositories import organization as organization_repository
from app.db.session import get_db
from app.schemas.agent import AgentCreate, AgentRead
from app.schemas.agent_version import AgentVersionCreate, AgentVersionRead, VersionDiff
from app.schemas.capability_trust import (
    CapabilityTrustRead,
    ContinuityEvaluationRequest,
    ContinuityEvaluationResponse,
    ReauthorizationRequest,
)
from app.services import agent as agents
from app.services import agent_version as versions
from app.services import trust_continuity

router = APIRouter(prefix="/agents", tags=["agents"])
logger = logging.getLogger(__name__)


def _agent_or_404(db: Session, agent_id: uuid.UUID):
    agent = agents.get(db, agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.post("", response_model=AgentRead, status_code=status.HTTP_201_CREATED)
def create_agent(payload: AgentCreate, db: Session = Depends(get_db)) -> AgentRead:
    if organization_repository.get(db, payload.organization_id) is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    try:
        return agents.create(db, payload)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="external_agent_id already exists for this organization"
        ) from exc


@router.get("/{agent_id}", response_model=AgentRead)
def get_agent(agent_id: uuid.UUID, db: Session = Depends(get_db)) -> AgentRead:
    return _agent_or_404(db, agent_id)


@router.post(
    "/{agent_id}/versions", response_model=AgentVersionRead, status_code=status.HTTP_201_CREATED
)
def create_version(
    agent_id: uuid.UUID, payload: AgentVersionCreate, db: Session = Depends(get_db)
) -> AgentVersionRead:
    _agent_or_404(db, agent_id)
    try:
        created = versions.create(db, agent_id, payload)
        logger.info("registered agent version: agent_id=%s version=%s", agent_id, created.version)
        return created
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="Version already exists for this agent"
        ) from exc


@router.get("/{agent_id}/versions", response_model=list[AgentVersionRead])
def list_versions(agent_id: uuid.UUID, db: Session = Depends(get_db)) -> list[AgentVersionRead]:
    _agent_or_404(db, agent_id)
    return versions.list_for_agent(db, agent_id)


@router.get("/{agent_id}/versions/{version_id}", response_model=AgentVersionRead)
def get_version(
    agent_id: uuid.UUID, version_id: uuid.UUID, db: Session = Depends(get_db)
) -> AgentVersionRead:
    _agent_or_404(db, agent_id)
    version = versions.get(db, agent_id, version_id)
    if version is None:
        raise HTTPException(status_code=404, detail="Agent version not found")
    return version


@router.get(
    "/{agent_id}/versions/{version_id}/capabilities", response_model=list[CapabilityTrustRead]
)
def list_capability_trust(
    agent_id: uuid.UUID, version_id: uuid.UUID, db: Session = Depends(get_db)
) -> list[CapabilityTrustRead]:
    _agent_or_404(db, agent_id)
    if versions.get(db, agent_id, version_id) is None:
        raise HTTPException(status_code=404, detail="Agent version not found")
    return capability_trust_repository.list_for_version(db, version_id)


@router.get("/{agent_id}/versions/{version_id}/diff/{other_version_id}", response_model=VersionDiff)
def diff_versions(
    agent_id: uuid.UUID,
    version_id: uuid.UUID,
    other_version_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> VersionDiff:
    _agent_or_404(db, agent_id)
    version = versions.get(db, agent_id, version_id)
    other = versions.get(db, agent_id, other_version_id)
    if version is None or other is None:
        raise HTTPException(status_code=404, detail="Agent version not found")
    return versions.diff(version, other)


@router.post(
    "/{agent_id}/versions/{version_id}/evaluate-continuity",
    response_model=ContinuityEvaluationResponse,
)
def evaluate_continuity(
    agent_id: uuid.UUID,
    version_id: uuid.UUID,
    payload: ContinuityEvaluationRequest,
    db: Session = Depends(get_db),
) -> ContinuityEvaluationResponse:
    _agent_or_404(db, agent_id)
    target_version = versions.get(db, agent_id, version_id)
    previous_version = versions.get(db, agent_id, payload.previous_version_id)
    if target_version is None or previous_version is None:
        raise HTTPException(status_code=404, detail="Agent version not found")
    version_diff = versions.diff(previous_version, target_version)
    return trust_continuity.evaluate_trust_continuity(
        db, previous_version, target_version, version_diff
    )


@router.post(
    "/{agent_id}/versions/{version_id}/capabilities/{capability_name}/reauthorize",
    response_model=CapabilityTrustRead,
)
def reauthorize_capability(
    agent_id: uuid.UUID,
    version_id: uuid.UUID,
    capability_name: str,
    payload: ReauthorizationRequest,
    db: Session = Depends(get_db),
) -> CapabilityTrustRead:
    _agent_or_404(db, agent_id)
    version = versions.get(db, agent_id, version_id)
    if version is None:
        raise HTTPException(status_code=404, detail="Agent version not found")
    try:
        return trust_continuity.explicitly_reauthorize(db, version, capability_name, payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
