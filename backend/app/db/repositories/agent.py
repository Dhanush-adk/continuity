import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.agent import Agent


def add(db: Session, agent: Agent) -> Agent:
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent


def get(db: Session, agent_id: uuid.UUID) -> Agent | None:
    return db.scalar(select(Agent).where(Agent.id == agent_id))


def get_by_external_id(
    db: Session, organization_id: uuid.UUID, external_agent_id: str
) -> Agent | None:
    return db.scalar(
        select(Agent).where(
            Agent.organization_id == organization_id,
            Agent.external_agent_id == external_agent_id,
        )
    )


def list_for_organization(db: Session, organization_id: uuid.UUID) -> list[Agent]:
    return list(
        db.scalars(
            select(Agent).where(Agent.organization_id == organization_id).order_by(Agent.created_at)
        )
    )
