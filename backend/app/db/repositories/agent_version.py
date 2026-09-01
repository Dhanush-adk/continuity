import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.agent_version import AgentVersion


def add(db: Session, version: AgentVersion) -> AgentVersion:
    db.add(version)
    db.commit()
    db.refresh(version)
    return version


def list_for_agent(db: Session, agent_id: uuid.UUID) -> list[AgentVersion]:
    return list(db.scalars(select(AgentVersion).where(AgentVersion.agent_id == agent_id)))


def get(db: Session, agent_id: uuid.UUID, version_id: uuid.UUID) -> AgentVersion | None:
    return db.scalar(
        select(AgentVersion).where(AgentVersion.agent_id == agent_id, AgentVersion.id == version_id)
    )
