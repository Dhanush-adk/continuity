"""Register and evaluate the complete procurement-agent demo scenario."""

import json
import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.repositories import agent as agent_repository
from app.db.repositories import organization as organization_repository
from app.db.session import SessionLocal
from app.models.agent import Agent
from app.models.organization import Organization
from app.schemas.agent_version import AgentVersionCreate
from app.schemas.authorization import AuthorizationRequest
from app.schemas.capability_trust import ReauthorizationRequest
from app.schemas.mandate import MandateExtractRequest
from app.schemas.organization_policy import OrganizationPolicyUpsert
from app.services import (
    agent_version,
    authorization,
    mandate,
    organization_policy,
    trust_continuity,
)
from app.services.intent_extractor import MockIntentExtractor


def _create_if_missing(db: Session, agent_id: uuid.UUID, payload: AgentVersionCreate):
    for existing in agent_version.list_for_agent(db, agent_id):
        if existing.version == payload.version:
            return existing
    try:
        return agent_version.create(db, agent_id, payload)
    except IntegrityError:
        db.rollback()
        return next(
            version
            for version in agent_version.list_for_agent(db, agent_id)
            if version.version == payload.version
        )


def seed(db: Session):
    organization = organization_repository.get_by_name(db, "Acme Corp")
    if organization is None:
        organization = organization_repository.add(db, Organization(name="Acme Corp"))
    agent = agent_repository.get_by_external_id(db, organization.id, "procurement-agent")
    if agent is None:
        agent = agent_repository.add(
            db,
            Agent(
                organization_id=organization.id,
                external_agent_id="procurement-agent",
                name="Procurement Agent",
                description="Demonstrates deployment identity and version diffing.",
            ),
        )
    v1 = _create_if_missing(
        db,
        agent.id,
        AgentVersionCreate(
            version="1.0.0",
            model_name="model-a",
            prompt_hash="procurement-prompt-v1",
            code_hash="procurement-code-v1",
            tool_manifest=[
                {"name": "search_catalog", "risk": "read"},
                {"name": "create_purchase_order", "risk": "write"},
                {"name": "execute_payment", "risk": "financial"},
            ],
            capability_manifest={
                "catalog.read": {"enabled": True},
                "purchase.create": {"enabled": True},
                "payment.execute": {"enabled": True, "constraints": {"max_amount": 15_000}},
            },
            permissions={"payment.execute": {"max_amount": 15_000}},
        ),
    )
    v2 = _create_if_missing(
        db,
        agent.id,
        AgentVersionCreate(
            version="1.1.0",
            model_name="model-b",
            prompt_hash="procurement-prompt-v1",
            code_hash="procurement-code-v1",
            tool_manifest=[
                {"name": "search_catalog", "risk": "read"},
                {"name": "create_purchase_order", "risk": "write"},
                {"name": "execute_payment", "risk": "financial"},
                {"name": "bank_transfer", "risk": "financial"},
            ],
            capability_manifest={
                "catalog.read": {"enabled": True},
                "purchase.create": {"enabled": True},
                "payment.execute": {"enabled": True, "constraints": {"max_amount": 100_000}},
                "bank.transfer": {"enabled": True},
            },
            permissions={"payment.execute": {"max_amount": 100_000}},
        ),
    )
    return agent, agent_version.diff(v1, v2)


def seed_continuity(db: Session):
    agent, comparison = seed(db)
    versions = {version.version: version for version in agent_version.list_for_agent(db, agent.id)}
    v1, v2 = versions["1.0.0"], versions["1.1.0"]
    for capability_name, envelope in {
        "catalog.read": {},
        "purchase.create": {},
        "payment.execute": {"max_amount": 15_000},
    }.items():
        trust_continuity.explicitly_reauthorize(
            db,
            v1,
            capability_name,
            ReauthorizationRequest(
                autonomy_constraints=envelope,
                reason="Initial procurement capability trust",
            ),
        )
    continuity = trust_continuity.evaluate_trust_continuity(db, v1, v2, comparison)
    bank_transfer = trust_continuity.explicitly_reauthorize(
        db,
        v2,
        "bank.transfer",
        ReauthorizationRequest(
            autonomy_constraints={"max_amount": 5_000},
            reason="Explicit procurement demo reauthorization",
        ),
    )
    return agent, comparison, continuity, bank_transfer


def _active_mandate(db: Session, agent: Agent, max_amount: int):
    draft = mandate.extract_and_create(
        db,
        MandateExtractRequest(
            organization_id=agent.organization_id,
            requester_id="employee-123",
            agent_id=agent.id,
            text=(
                "Purchase 10 GPUs for the ML team from an approved vendor. "
                f"Maximum ${max_amount:,}."
            ),
        ),
        MockIntentExtractor(),
    )
    return mandate.activate(db, draft)


def _authorization_request(agent: Agent, version_id: uuid.UUID, mandate_id: uuid.UUID, **action):
    return AuthorizationRequest(
        organization_id=agent.organization_id,
        agent_id=agent.id,
        agent_version_id=version_id,
        capability="payment.execute",
        mandate_id=mandate_id,
        action={
            "action_type": "purchase",
            "item_category": "gpu",
            "quantity": 10,
            "amount": 13_900,
            "currency": "USD",
            "vendor": "CDW",
            "purpose": "ML team",
            **action,
        },
    )


def seed_authorization_demo(db: Session):
    agent, comparison, continuity, bank_transfer = seed_continuity(db)
    versions = {version.version: version for version in agent_version.list_for_agent(db, agent.id)}
    version = versions["1.1.0"]
    organization_policy.upsert(
        db,
        agent.organization_id,
        OrganizationPolicyUpsert(
            approved_vendors=["CDW", "Dell", "Apple"],
            approval_thresholds=[{"amount_gte": 25_000, "action": "REVIEW"}],
            hard_payment_limit=100_000,
        ),
    )
    standard = _active_mandate(db, agent, 15_000)
    larger = _active_mandate(db, agent, 30_000)
    allowed = authorization.authorize(db, _authorization_request(agent, version.id, standard.id))
    denied = authorization.authorize(
        db,
        _authorization_request(
            agent,
            version.id,
            standard.id,
            vendor="UnknownVendor",
            quantity=20,
            amount=27_800,
        ),
    )
    reviewed = authorization.authorize(
        db, _authorization_request(agent, version.id, larger.id, vendor="Dell", amount=27_000)
    )
    return (
        agent,
        comparison,
        continuity,
        bank_transfer,
        standard,
        allowed,
        denied,
        reviewed,
    )


def main() -> None:
    db = SessionLocal()
    try:
        (
            agent,
            comparison,
            continuity,
            bank_transfer,
            standard,
            allowed,
            denied,
            reviewed,
        ) = seed_authorization_demo(db)
        print(f"Agent: {agent.external_agent_id}")
        print(f"Versions: {comparison.from_version} -> {comparison.to_version}")
        print(comparison.model_dump_json(indent=2))
        print("Continuity evaluation before bank.transfer reauthorization:")
        print(continuity.model_dump_json(indent=2))
        print("bank.transfer after explicit reauthorization:")
        print(f"{bank_transfer.status.value} {bank_transfer.autonomy_constraints}")
        print("Activated structured mandate:")
        print(json.dumps(standard.structured_intent, indent=2, sort_keys=True))
        print("Authorization decisions:")
        print(f"ALLOW: {allowed.model_dump_json()}")
        print(f"DENY: {denied.model_dump_json()}")
        print(f"REVIEW: {reviewed.model_dump_json()}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
