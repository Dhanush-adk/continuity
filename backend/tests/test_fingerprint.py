import pytest

from app.services.fingerprint import deployment_fingerprint


def test_fingerprint_is_stable_when_json_key_order_changes() -> None:
    first = deployment_fingerprint(
        model_name="gpt-5",
        prompt_hash="prompt-a",
        code_hash="code-a",
        tool_manifest={"browser": {"scopes": ["read"]}, "email": {"scopes": ["send"]}},
        capability_manifest={"search": True, "summarize": True},
        permissions={"production": False, "spend_limit": 100},
    )
    second = deployment_fingerprint(
        model_name="gpt-5",
        prompt_hash="prompt-a",
        code_hash="code-a",
        tool_manifest={"email": {"scopes": ["send"]}, "browser": {"scopes": ["read"]}},
        capability_manifest={"summarize": True, "search": True},
        permissions={"spend_limit": 100, "production": False},
    )

    assert first == second
    assert len(first) == 64


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("prompt_hash", "prompt-b"),
        ("code_hash", "code-b"),
        ("tool_manifest", [{"name": "bank_transfer"}]),
        ("capability_manifest", {"bank.transfer": {"enabled": True}}),
        ("permissions", {"payment.execute": {"max_amount": 100_000}}),
    ],
)
def test_fingerprint_changes_for_each_material_input(field: str, replacement: object) -> None:
    common = {
        "model_name": "gpt-5",
        "prompt_hash": "prompt-a",
        "code_hash": "code-a",
        "tool_manifest": [],
        "capability_manifest": [],
        "permissions": [],
    }

    changed = deployment_fingerprint(**{**common, field: replacement})
    assert deployment_fingerprint(**common) != changed
