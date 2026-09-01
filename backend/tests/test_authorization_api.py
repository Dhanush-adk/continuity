from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import app
from app.schemas.mandate import ProcurementIntent
from app.services.intent_extractor import (
    MockIntentExtractor,
    get_intent_extractor,
    validate_candidate,
)


def _version(version: str, **changes: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "version": version,
        "model_name": "model-a",
        "prompt_hash": "prompt-a",
        "code_hash": "code-a",
        "tool_manifest": [{"name": "execute_payment", "risk": "financial"}],
        "capability_manifest": {
            "catalog.read": {"enabled": True},
            "purchase.create": {"enabled": True},
            "payment.execute": {"enabled": True, "constraints": {"max_amount": 15_000}},
            "bank.transfer": {"enabled": True},
        },
        "permissions": {},
    }
    payload.update(changes)
    return payload


def _setup_agent(client: TestClient, name: str = "Acme Authorization") -> tuple[str, str, str]:
    organization_id = client.post("/organizations", json={"name": name}).json()["id"]
    agent_id = client.post(
        "/agents",
        json={
            "organization_id": organization_id,
            "external_agent_id": name.lower().replace(" ", "-"),
            "name": "Procurement Agent",
        },
    ).json()["id"]
    v1 = client.post(f"/agents/{agent_id}/versions", json=_version("1.0.0")).json()
    for capability, constraints in {
        "catalog.read": {},
        "purchase.create": {},
        "payment.execute": {"max_amount": 15_000},
    }.items():
        response = client.post(
            f"/agents/{agent_id}/versions/{v1['id']}/capabilities/{capability}/reauthorize",
            json={"autonomy_constraints": constraints, "reason": "Authorization fixture trust"},
        )
        assert response.status_code == 200
    v2 = client.post(
        f"/agents/{agent_id}/versions",
        json=_version(
            "1.1.0",
            model_name="model-b",
            capability_manifest={
                "catalog.read": {"enabled": True},
                "purchase.create": {"enabled": True},
                "payment.execute": {"enabled": True, "constraints": {"max_amount": 100_000}},
                "bank.transfer": {"enabled": True},
            },
        ),
    ).json()
    evaluated = client.post(
        f"/agents/{agent_id}/versions/{v2['id']}/evaluate-continuity",
        json={"previous_version_id": v1["id"]},
    )
    assert evaluated.status_code == 200
    policy = client.put(
        f"/organizations/{organization_id}/policy",
        json={
            "approved_vendors": ["CDW", "Dell", "Apple"],
            "approval_thresholds": [{"amount_gte": 25_000, "action": "REVIEW"}],
            "hard_payment_limit": 100_000,
        },
    )
    assert policy.status_code == 200
    return organization_id, agent_id, v2["id"]


def _mandate(
    client: TestClient,
    organization_id: str,
    agent_id: str,
    *,
    amount: int = 15_000,
    activate: bool = True,
    expires_at: str | None = None,
) -> dict[str, Any]:
    response = client.post(
        "/mandates/extract",
        json={
            "organization_id": organization_id,
            "requester_id": "employee-123",
            "agent_id": agent_id,
            "text": (
                f"Purchase 10 GPUs for the ML team from an approved vendor. Maximum ${amount:,}."
            ),
            "expires_at": expires_at,
        },
    )
    assert response.status_code == 201
    mandate = response.json()
    if activate:
        active = client.post(f"/mandates/{mandate['id']}/activate")
        assert active.status_code == 200
        mandate = active.json()
    return mandate


def _request(
    organization_id: str,
    agent_id: str,
    version_id: str,
    mandate_id: str,
    **action_changes: Any,
) -> dict[str, Any]:
    action: dict[str, Any] = {
        "action_type": "purchase",
        "item_category": "gpu",
        "quantity": 10,
        "amount": 13_900,
        "currency": "USD",
        "vendor": "CDW",
        "purpose": "ML team",
    }
    action.update(action_changes)
    return {
        "organization_id": organization_id,
        "agent_id": agent_id,
        "agent_version_id": version_id,
        "capability": "payment.execute",
        "mandate_id": mandate_id,
        "action": action,
    }


def test_mock_extraction_is_deterministic_and_preserves_ambiguity() -> None:
    extractor = MockIntentExtractor()
    intent = extractor.extract("Buy some GPUs soon.")

    assert intent.action_type == "purchase"
    assert intent.item_category == "gpu"
    assert intent.quantity_max is None
    assert intent.max_amount is None
    with pytest.raises(ValidationError):
        validate_candidate({"quantity_max": "not-a-number"})


def test_extract_creates_draft_then_activation_makes_mandate_authoritative(
    client: TestClient,
) -> None:
    organization_id, agent_id, _ = _setup_agent(client, "Extraction Acme")
    draft = _mandate(client, organization_id, agent_id, activate=False)

    assert draft["status"] == "DRAFT"
    assert draft["raw_extraction"] == draft["structured_intent"]
    assert draft["canonicalization_issues"] == []
    assert draft["structured_intent"] == {
        "action_type": "purchase",
        "item_category": "gpu",
        "quantity_max": 10,
        "max_amount": 15_000,
        "currency": "USD",
        "vendor_policy": "approved_only",
        "approved_vendors": None,
        "purpose": "ML team",
    }
    assert client.post(f"/mandates/{draft['id']}/activate").json()["status"] == "ACTIVE"


def test_full_procurement_allow_deny_and_review_scenarios(client: TestClient) -> None:
    organization_id, agent_id, version_id = _setup_agent(client, "Procurement Scenarios")
    standard = _mandate(client, organization_id, agent_id)

    allowed = client.post(
        "/authorize", json=_request(organization_id, agent_id, version_id, standard["id"])
    )
    assert allowed.status_code == 200
    assert allowed.json()["decision"] == "ALLOW"

    denied = client.post(
        "/authorize",
        json=_request(
            organization_id,
            agent_id,
            version_id,
            standard["id"],
            vendor="UnknownVendor",
            quantity=20,
            amount=27_800,
        ),
    )
    denied_codes = {reason["code"] for reason in denied.json()["reasons"]}
    assert denied.json()["decision"] == "DENY"
    assert {
        "MANDATE_QUANTITY_EXCEEDED",
        "MANDATE_AMOUNT_EXCEEDED",
        "VENDOR_NOT_APPROVED",
    } <= denied_codes

    larger = _mandate(client, organization_id, agent_id, amount=30_000)
    reviewed = client.post(
        "/authorize",
        json=_request(organization_id, agent_id, version_id, larger["id"], amount=27_000),
    )
    review_codes = {reason["code"] for reason in reviewed.json()["reasons"]}
    assert reviewed.json()["decision"] == "REVIEW"
    assert {"TRUSTED_ENVELOPE_EXCEEDED", "ORGANIZATION_APPROVAL_REQUIRED"} <= review_codes


def test_mandate_and_policy_violations_deny_with_precedence(client: TestClient) -> None:
    organization_id, agent_id, version_id = _setup_agent(client, "Constraint Acme")
    mandate = _mandate(client, organization_id, agent_id)
    invalid_actions = [
        {"amount": 15_001},
        {"quantity": 11},
        {"item_category": "laptop"},
        {"vendor": "UnknownVendor"},
    ]
    for change in invalid_actions:
        response = client.post(
            "/authorize",
            json=_request(organization_id, agent_id, version_id, mandate["id"], **change),
        )
        assert response.json()["decision"] == "DENY"

    response = client.post(
        "/authorize",
        json=_request(
            organization_id,
            agent_id,
            version_id,
            mandate["id"],
            amount=200_000,
        ),
    )
    assert response.json()["decision"] == "DENY"
    assert "MANDATE_AMOUNT_EXCEEDED" in {reason["code"] for reason in response.json()["reasons"]}


def test_explicitly_trusted_capability_inside_envelope_can_proceed(client: TestClient) -> None:
    organization_id, agent_id, version_id = _setup_agent(client, "Trusted Envelope")
    reauthorized = client.post(
        f"/agents/{agent_id}/versions/{version_id}/capabilities/payment.execute/reauthorize",
        json={"autonomy_constraints": {"max_amount": 15_000}, "reason": "Test approval"},
    )
    assert reauthorized.json()["status"] == "TRUSTED"
    mandate = _mandate(client, organization_id, agent_id)

    response = client.post(
        "/authorize", json=_request(organization_id, agent_id, version_id, mandate["id"])
    )

    assert response.json()["decision"] == "ALLOW"
    assert response.json()["checks"]["capability"]["trust_status"] == "TRUSTED"


def test_inactive_expired_wrong_org_and_untrusted_capability_are_denied(client: TestClient) -> None:
    organization_id, agent_id, version_id = _setup_agent(client, "Mandate States")
    draft = _mandate(client, organization_id, agent_id, activate=False)
    inactive = client.post(
        "/authorize", json=_request(organization_id, agent_id, version_id, draft["id"])
    )
    assert "MANDATE_NOT_ACTIVE" in {reason["code"] for reason in inactive.json()["reasons"]}

    expired = _mandate(
        client,
        organization_id,
        agent_id,
        expires_at=(datetime.now(UTC) - timedelta(minutes=1)).isoformat(),
    )
    expired_result = client.post(
        "/authorize", json=_request(organization_id, agent_id, version_id, expired["id"])
    )
    assert "MANDATE_EXPIRED" in {reason["code"] for reason in expired_result.json()["reasons"]}

    other_organization = client.post("/organizations", json={"name": "Other Org"}).json()["id"]
    wrong_org_mandate = _mandate(client, other_organization, None, activate=True)
    wrong_org = client.post(
        "/authorize", json=_request(organization_id, agent_id, version_id, wrong_org_mandate["id"])
    )
    assert "MANDATE_ORGANIZATION_MISMATCH" in {
        reason["code"] for reason in wrong_org.json()["reasons"]
    }

    untrusted = client.post(
        "/authorize",
        json={
            **_request(
                organization_id,
                agent_id,
                version_id,
                _mandate(client, organization_id, agent_id)["id"],
            ),
            "capability": "bank.transfer",
        },
    )
    assert "CAPABILITY_UNTRUSTED" in {reason["code"] for reason in untrusted.json()["reasons"]}


def test_review_is_separate_from_original_decision_and_uses_snapshot(client: TestClient) -> None:
    organization_id, agent_id, version_id = _setup_agent(client, "Review Audit")
    mandate = _mandate(client, organization_id, agent_id, amount=30_000)
    authorization_result = client.post(
        "/authorize",
        json=_request(organization_id, agent_id, version_id, mandate["id"], amount=27_000),
    )
    assert authorization_result.json()["decision"] == "REVIEW"
    decision_id = authorization_result.json()["decision_id"]

    reviewed = client.post(
        f"/authorizations/{decision_id}/review",
        json={
            "decision": "APPROVE",
            "reviewer_id": "procurement-director",
            "reviewer_name": "Avery Director",
            "reason": "Approved for ML expansion",
        },
    )
    assert reviewed.status_code == 201
    assert reviewed.json()["decision"] == "APPROVE"

    detail = client.get(f"/authorizations/{decision_id}")
    assert detail.status_code == 200
    assert detail.json()["decision"] == "REVIEW"
    assert detail.json()["review"]["reviewer_id"] == "procurement-director"
    assert detail.json()["mandate_snapshot"]["structured_intent"]["max_amount"] == 30_000
    assert detail.json()["mandate_snapshot"]["raw_intent"].startswith("Purchase 10 GPUs")
    assert (
        client.post(
            f"/authorizations/{decision_id}/review",
            json={"decision": "DENY", "reviewer_id": "other", "reason": "Duplicate"},
        ).status_code
        == 409
    )


def test_authorization_feed_and_capability_trust_read_endpoints(client: TestClient) -> None:
    organization_id, agent_id, version_id = _setup_agent(client, "Feed Read")
    mandate = _mandate(client, organization_id, agent_id)
    client.post("/authorize", json=_request(organization_id, agent_id, version_id, mandate["id"]))

    assert client.get("/organizations").status_code == 200
    assert client.get(f"/organizations/{organization_id}/agents").json()[0]["id"] == agent_id
    assert client.get(f"/agents/{agent_id}/versions/{version_id}/capabilities").status_code == 200
    feed = client.get(f"/authorizations?organization_id={organization_id}")
    assert feed.status_code == 200
    assert feed.json()[0]["capability_name"] == "payment.execute"


def test_unsupported_canonicalization_issue_blocks_activation(client: TestClient) -> None:
    organization_id, agent_id, _ = _setup_agent(client, "Canonicalization Safety")
    app.dependency_overrides[get_intent_extractor] = lambda: MockIntentExtractor(
        ProcurementIntent(
            action_type="acquire",
            item_category="accelerator",
            quantity_max=12,
            max_amount=14_500,
            currency="USD",
        )
    )
    response = client.post(
        "/mandates/extract",
        json={
            "organization_id": organization_id,
            "requester_id": "employee-123",
            "agent_id": agent_id,
            "text": "Acquire an accelerator for research, maximum $14,500.",
        },
    )
    assert response.status_code == 201
    draft = response.json()
    assert draft["raw_extraction"]["action_type"] == "acquire"
    assert draft["structured_intent"]["action_type"] == "acquire"
    assert {issue["code"] for issue in draft["canonicalization_issues"]} == {
        "UNSUPPORTED_ACTION_TYPE",
        "UNSUPPORTED_ITEM_CATEGORY",
    }
    activation = client.post(f"/mandates/{draft['id']}/activate")
    assert activation.status_code == 409
    assert "UNSUPPORTED_ACTION_TYPE" in activation.json()["detail"]
