from fastapi.testclient import TestClient


def _version(version: str, **changes: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "version": version,
        "model_name": "gpt-5",
        "prompt_hash": "prompt-v1",
        "code_hash": "code-v1",
        "tool_manifest": [{"name": "search", "risk": "read"}],
        "capability_manifest": {"research": True},
        "permissions": {"send_email": False},
    }
    payload.update(changes)
    return payload


def test_create_and_retrieve_agent_with_versions(client: TestClient) -> None:
    organization = client.post("/organizations", json={"name": "Acme"})
    assert organization.status_code == 201

    agent = client.post(
        "/agents",
        json={
            "organization_id": organization.json()["id"],
            "external_agent_id": "researcher-prod",
            "name": "Researcher",
            "description": "Finds procurement information.",
        },
    )
    assert agent.status_code == 201
    assert agent.json()["description"] == "Finds procurement information."
    agent_id = agent.json()["id"]

    created_version = client.post(f"/agents/{agent_id}/versions", json=_version("1.0.0"))
    assert created_version.status_code == 201
    assert len(created_version.json()["deployment_fingerprint"]) == 64

    assert client.get(f"/agents/{agent_id}").json()["name"] == "Researcher"
    versions = client.get(f"/agents/{agent_id}/versions")
    assert versions.status_code == 200
    assert [item["version"] for item in versions.json()] == ["1.0.0"]
    version_id = created_version.json()["id"]
    assert client.get(f"/agents/{agent_id}/versions/{version_id}").status_code == 200
    duplicate_version = client.post(f"/agents/{agent_id}/versions", json=_version("1.0.0"))
    assert duplicate_version.status_code == 409


def test_diff_groups_version_changes(client: TestClient) -> None:
    organization_id = client.post("/organizations", json={"name": "Acme"}).json()["id"]
    agent_id = client.post(
        "/agents",
        json={"organization_id": organization_id, "external_agent_id": "ops", "name": "Ops"},
    ).json()["id"]
    first = client.post(f"/agents/{agent_id}/versions", json=_version("1.0.0")).json()
    second = client.post(
        f"/agents/{agent_id}/versions",
        json=_version(
            "2.0.0",
            model_name="gpt-5.1",
            prompt_hash="prompt-v2",
            code_hash="code-v2",
            tool_manifest=[
                {"name": "search", "risk": "read"},
                {"name": "email", "risk": "write"},
            ],
            capability_manifest={"summarize": True},
            permissions={"send_email": True},
        ),
    ).json()

    response = client.get(f"/agents/{agent_id}/versions/{first['id']}/diff/{second['id']}")
    assert response.status_code == 200
    assert response.json() == {
        "from_version": "1.0.0",
        "to_version": "2.0.0",
        "changed": True,
        "model": {"changed": True, "before": "gpt-5", "after": "gpt-5.1"},
        "prompt": {"changed": True, "before": "prompt-v1", "after": "prompt-v2"},
        "code": {"changed": True, "before": "code-v1", "after": "code-v2"},
        "tools": {"added": ["email"], "removed": []},
        "capabilities": {
            "added": ["summarize"],
            "removed": ["research"],
            "modified": [],
        },
        "permissions": {
            "changed": True,
            "changes": [{"name": "send_email", "before": False, "after": True}],
        },
    }


def test_meaningful_not_found_and_conflict_errors(client: TestClient) -> None:
    assert client.get("/agents/00000000-0000-0000-0000-000000000000").status_code == 404
    assert (
        client.post(
            "/agents",
            json={
                "organization_id": "00000000-0000-0000-0000-000000000000",
                "external_agent_id": "missing-org",
                "name": "Missing",
            },
        ).status_code
        == 404
    )

    assert client.post("/organizations", json={"name": "Only once"}).status_code == 201
    duplicate = client.post("/organizations", json={"name": "Only once"})
    assert duplicate.status_code == 409


def test_unknown_version_returns_not_found(client: TestClient) -> None:
    organization_id = client.post("/organizations", json={"name": "Unknown Version Co"}).json()[
        "id"
    ]
    agent_id = client.post(
        "/agents",
        json={
            "organization_id": organization_id,
            "external_agent_id": "unknown",
            "name": "Unknown",
        },
    ).json()["id"]

    response = client.get(f"/agents/{agent_id}/versions/00000000-0000-0000-0000-000000000000")

    assert response.status_code == 404


def test_invalid_manifests_return_validation_errors(client: TestClient) -> None:
    organization_id = client.post("/organizations", json={"name": "Validation Co"}).json()["id"]
    agent_id = client.post(
        "/agents",
        json={
            "organization_id": organization_id,
            "external_agent_id": "validator",
            "name": "Validator",
        },
    ).json()["id"]

    response = client.post(
        f"/agents/{agent_id}/versions",
        json=_version("1.0.0", tool_manifest=[{"name": "duplicate"}, {"name": "duplicate"}]),
    )

    assert response.status_code == 422
