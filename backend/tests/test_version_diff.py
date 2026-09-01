from typing import Any

import pytest

from app.models.agent_version import AgentVersion
from app.services.agent_version import diff


def _version(version: str, **overrides: Any) -> AgentVersion:
    values: dict[str, Any] = {
        "version": version,
        "model_name": "model-a",
        "prompt_hash": "prompt-a",
        "code_hash": "code-a",
        "tool_manifest": [{"name": "search_catalog", "risk": "read"}],
        "capability_manifest": {"catalog.read": {"enabled": True}},
        "permissions": {"production": False},
        "deployment_fingerprint": "unused-in-diff",
    }
    values.update(overrides)
    return AgentVersion(**values)


def test_diff_with_no_meaningful_difference() -> None:
    result = diff(_version("1.0.0"), _version("1.1.0"))

    assert result.changed is False
    assert result.model.changed is False
    assert result.tools.added == []
    assert result.capabilities.modified == []
    assert result.permissions.changed is False


@pytest.mark.parametrize(
    ("before_tools", "after_tools", "added", "removed"),
    [
        (
            [{"name": "search_catalog"}],
            [{"name": "bank_transfer"}],
            ["bank_transfer"],
            ["search_catalog"],
        ),
        (
            [{"name": "search_catalog"}],
            [{"name": "search_catalog"}, {"name": "bank_transfer"}],
            ["bank_transfer"],
            [],
        ),
    ],
)
def test_diff_reports_tool_changes(
    before_tools: list[dict[str, str]],
    after_tools: list[dict[str, str]],
    added: list[str],
    removed: list[str],
) -> None:
    result = diff(
        _version("1.0.0", tool_manifest=before_tools),
        _version("1.1.0", tool_manifest=after_tools),
    )

    assert result.tools.added == added
    assert result.tools.removed == removed


def test_diff_reports_capability_add_remove_and_modification() -> None:
    before = _version(
        "1.0.0",
        capability_manifest={
            "catalog.read": {"enabled": True},
            "payment.execute": {"constraints": {"max_amount": 15_000}},
        },
    )
    after = _version(
        "1.1.0",
        capability_manifest={
            "bank.transfer": {"enabled": True},
            "payment.execute": {"constraints": {"max_amount": 100_000}},
        },
    )

    result = diff(before, after)

    assert result.capabilities.added == ["bank.transfer"]
    assert result.capabilities.removed == ["catalog.read"]
    assert result.capabilities.modified[0].model_dump() == {
        "name": "payment.execute",
        "before": {"constraints": {"max_amount": 15_000}},
        "after": {"constraints": {"max_amount": 100_000}},
    }


def test_diff_reports_permission_change() -> None:
    result = diff(
        _version("1.0.0", permissions={"payment.execute": {"max_amount": 15_000}}),
        _version("1.1.0", permissions={"payment.execute": {"max_amount": 100_000}}),
    )

    assert result.permissions.changed is True
    assert result.permissions.changes[0].name == "payment.execute"
