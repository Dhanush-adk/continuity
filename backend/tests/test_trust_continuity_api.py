from typing import Any

from fastapi.testclient import TestClient


def _version(version: str, **changes: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "version": version,
        "model_name": "model-a",
        "prompt_hash": "prompt-a",
        "code_hash": "code-a",
        "tool_manifest": [{"name": "search_catalog", "risk": "read"}],
        "capability_manifest": {
            "catalog.read": {"enabled": True},
            "purchase.create": {"enabled": True},
            "payment.execute": {"enabled": True, "constraints": {"max_amount": 15_000}},
        },
        "permissions": {},
    }
    payload.update(changes)
    return payload


def _agent(client: TestClient, name: str) -> str:
    organization_id = client.post("/organizations", json={"name": name}).json()["id"]
    return client.post(
        "/agents",
        json={
            "organization_id": organization_id,
            "external_agent_id": name.lower().replace(" ", "-"),
            "name": name,
        },
    ).json()["id"]


def _reauthorize_initial_trust(client: TestClient, agent_id: str, version_id: str) -> None:
    constraints = {
        "catalog.read": {},
        "purchase.create": {},
        "payment.execute": {"max_amount": 15_000},
    }
    for capability_name, envelope in constraints.items():
        response = client.post(
            f"/agents/{agent_id}/versions/{version_id}/capabilities/{capability_name}/reauthorize",
            json={"autonomy_constraints": envelope, "reason": "Initial demo trust"},
        )
        assert response.status_code == 200


def test_procurement_continuity_preserves_only_prior_financial_envelope(client: TestClient) -> None:
    agent_id = _agent(client, "Acme Procurement")
    v1 = client.post(f"/agents/{agent_id}/versions", json=_version("1.0.0")).json()
    _reauthorize_initial_trust(client, agent_id, v1["id"])
    v2 = client.post(
        f"/agents/{agent_id}/versions",
        json=_version(
            "1.1.0",
            model_name="model-b",
            tool_manifest=[
                {"name": "search_catalog", "risk": "read"},
                {"name": "bank_transfer", "risk": "financial"},
            ],
            capability_manifest={
                "catalog.read": {"enabled": True},
                "purchase.create": {"enabled": True},
                "payment.execute": {"enabled": True, "constraints": {"max_amount": 100_000}},
                "bank.transfer": {"enabled": True},
            },
        ),
    ).json()

    endpoint = f"/agents/{agent_id}/versions/{v2['id']}/evaluate-continuity"
    response = client.post(endpoint, json={"previous_version_id": v1["id"]})
    assert response.status_code == 200
    result = response.json()
    by_name = {item["capability_name"]: item for item in result["capabilities"]}

    assert result["summary"] == {"inherited": 2, "restricted": 1, "reauthorization_required": 1}
    assert by_name["catalog.read"]["decision"] == "INHERIT"
    assert by_name["purchase.create"]["resulting_status"] == "TRUSTED"
    assert by_name["payment.execute"] == {
        "capability_name": "payment.execute",
        "decision": "RESTRICT",
        "resulting_status": "LIMITED",
        "change_severity": "CRITICAL",
        "inherited_from_version_id": v1["id"],
        "autonomy_constraints": {"max_amount": 15_000},
        "reasons": ["FINANCIAL_AUTHORITY_INCREASED", "PREVIOUS_TRUST_ENVELOPE_RETAINED"],
        "explicitly_reauthorized": False,
    }
    assert by_name["bank.transfer"]["decision"] == "REAUTHORIZE"
    assert by_name["bank.transfer"]["resulting_status"] == "UNTRUSTED"

    repeated = client.post(endpoint, json={"previous_version_id": v1["id"]})
    assert repeated.json() == result

    reauthorized = client.post(
        f"/agents/{agent_id}/versions/{v2['id']}/capabilities/bank.transfer/reauthorize",
        json={"autonomy_constraints": {"max_amount": 5_000}, "reason": "Demo approval"},
    )
    assert reauthorized.status_code == 200
    assert reauthorized.json()["status"] == "TRUSTED"
    assert reauthorized.json()["autonomy_constraints"] == {"max_amount": 5_000}


def test_model_change_restricts_sensitive_capability_but_not_read_or_write(
    client: TestClient,
) -> None:
    agent_id = _agent(client, "Model Change")
    v1 = client.post(f"/agents/{agent_id}/versions", json=_version("1.0.0")).json()
    _reauthorize_initial_trust(client, agent_id, v1["id"])
    v2 = client.post(
        f"/agents/{agent_id}/versions",
        json=_version("1.1.0", model_name="model-b"),
    ).json()

    response = client.post(
        f"/agents/{agent_id}/versions/{v2['id']}/evaluate-continuity",
        json={"previous_version_id": v1["id"]},
    )
    by_name = {item["capability_name"]: item for item in response.json()["capabilities"]}

    assert by_name["catalog.read"]["decision"] == "INHERIT"
    assert by_name["purchase.create"]["decision"] == "INHERIT"
    assert by_name["payment.execute"]["decision"] == "RESTRICT"
    assert by_name["payment.execute"]["change_severity"] == "MATERIAL"


def test_enabled_capability_requires_reauthorization_and_removed_has_no_state(
    client: TestClient,
) -> None:
    agent_id = _agent(client, "Capability Changes")
    v1 = client.post(
        f"/agents/{agent_id}/versions",
        json=_version(
            "1.0.0",
            capability_manifest={
                "catalog.read": {"enabled": True},
                "purchase.create": {"enabled": False},
                "payment.execute": {"enabled": True, "constraints": {"max_amount": 15_000}},
            },
        ),
    ).json()
    _reauthorize_initial_trust(client, agent_id, v1["id"])
    v2 = client.post(
        f"/agents/{agent_id}/versions",
        json=_version(
            "1.1.0",
            capability_manifest={
                "purchase.create": {"enabled": True},
                "payment.execute": {"enabled": True, "constraints": {"max_amount": 15_000}},
            },
        ),
    ).json()

    response = client.post(
        f"/agents/{agent_id}/versions/{v2['id']}/evaluate-continuity",
        json={"previous_version_id": v1["id"]},
    )
    capabilities = {item["capability_name"]: item for item in response.json()["capabilities"]}

    assert "catalog.read" not in capabilities
    assert capabilities["purchase.create"]["decision"] == "REAUTHORIZE"
    assert capabilities["purchase.create"]["resulting_status"] == "UNTRUSTED"


def test_unknown_and_cross_agent_versions_are_rejected(client: TestClient) -> None:
    first_agent = _agent(client, "First Agent")
    second_agent = _agent(client, "Second Agent")
    first_version = client.post(f"/agents/{first_agent}/versions", json=_version("1.0.0")).json()
    second_version = client.post(f"/agents/{second_agent}/versions", json=_version("1.0.0")).json()

    unknown = client.post(
        f"/agents/{first_agent}/versions/{first_version['id']}/evaluate-continuity",
        json={"previous_version_id": "00000000-0000-0000-0000-000000000000"},
    )
    cross_agent = client.post(
        f"/agents/{first_agent}/versions/{first_version['id']}/evaluate-continuity",
        json={"previous_version_id": second_version["id"]},
    )

    assert unknown.status_code == 404
    assert cross_agent.status_code == 404
