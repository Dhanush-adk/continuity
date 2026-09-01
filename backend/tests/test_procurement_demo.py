from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app import models  # noqa: F401 -- registers ORM mappings
from app.db.base import Base
from scripts.seed_procurement_demo import seed, seed_authorization_demo, seed_continuity


def test_procurement_demo_seeds_expected_version_evidence() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        agent, comparison = seed(session)

        assert agent.external_agent_id == "procurement-agent"
        assert comparison.from_version == "1.0.0"
        assert comparison.to_version == "1.1.0"
        assert comparison.model.changed is True
        assert comparison.tools.added == ["bank_transfer"]
        assert comparison.capabilities.added == ["bank.transfer"]
        assert comparison.capabilities.modified[0].name == "payment.execute"
        assert comparison.capabilities.modified[0].before["constraints"]["max_amount"] == 15_000
        assert comparison.capabilities.modified[0].after["constraints"]["max_amount"] == 100_000

    Base.metadata.drop_all(engine)
    engine.dispose()


def test_procurement_demo_runs_all_day_three_authorization_scenarios() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        _, _, _, _, _, allowed, denied, reviewed = seed_authorization_demo(session)

        assert allowed.decision.value == "ALLOW"
        assert denied.decision.value == "DENY"
        assert reviewed.decision.value == "REVIEW"

    Base.metadata.drop_all(engine)
    engine.dispose()


def test_procurement_demo_shows_continuity_and_bounded_reauthorization() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        _, _, continuity, bank_transfer = seed_continuity(session)
        decisions = {item.capability_name: item for item in continuity.capabilities}

        assert decisions["catalog.read"].decision.value == "INHERIT"
        assert decisions["purchase.create"].decision.value == "INHERIT"
        assert decisions["payment.execute"].decision.value == "RESTRICT"
        assert decisions["payment.execute"].autonomy_constraints == {"max_amount": 15_000}
        assert decisions["bank.transfer"].decision.value == "REAUTHORIZE"
        assert bank_transfer.status.value == "TRUSTED"
        assert bank_transfer.autonomy_constraints == {"max_amount": 5_000}

    Base.metadata.drop_all(engine)
    engine.dispose()
