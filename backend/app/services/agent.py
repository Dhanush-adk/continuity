import uuid

from sqlalchemy.orm import Session

from app.db.repositories import agent as agents
from app.models.agent import Agent
from app.schemas.agent import AgentCreate


def create(db: Session, payload: AgentCreate) -> Agent:
    return agents.add(db, Agent(**payload.model_dump()))


def get(db: Session, agent_id: uuid.UUID) -> Agent | None:
    return agents.get(db, agent_id)
