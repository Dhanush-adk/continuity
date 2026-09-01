from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from app.models.agent_version import AgentVersion
from app.schemas.agent_version import VersionDiff
from app.services.capability_metadata import metadata_for


class ChangeSeverity(StrEnum):
    SAFE = "SAFE"
    MATERIAL = "MATERIAL"
    CRITICAL = "CRITICAL"


@dataclass(frozen=True)
class CapabilityChange:
    severity: ChangeSeverity
    reason_codes: list[str]


def _enabled(value: dict[str, Any]) -> bool:
    return value.get("enabled") is True


def _max_amount(value: dict[str, Any]) -> int | float | None:
    constraints = value.get("constraints")
    if not isinstance(constraints, dict):
        return None
    amount = constraints.get("max_amount")
    return amount if isinstance(amount, (int, float)) and not isinstance(amount, bool) else None


def classify_capability_change(
    previous_version: AgentVersion,
    new_version: AgentVersion,
    version_diff: VersionDiff,
    capability_name: str,
) -> CapabilityChange:
    """Classify configuration evidence, never a final action authorization outcome."""
    before = previous_version.capability_manifest.get(capability_name)
    after = new_version.capability_manifest.get(capability_name)
    metadata = metadata_for(capability_name)

    if before is None and after is not None:
        if metadata.sensitive:
            return CapabilityChange(ChangeSeverity.CRITICAL, ["NEW_SENSITIVE_CAPABILITY"])
        return CapabilityChange(ChangeSeverity.MATERIAL, ["NEW_CAPABILITY"])
    if not isinstance(before, dict) or not isinstance(after, dict):
        return CapabilityChange(ChangeSeverity.MATERIAL, ["CAPABILITY_CONFIGURATION_CHANGED"])
    if not _enabled(before) and _enabled(after):
        return CapabilityChange(ChangeSeverity.CRITICAL, ["CAPABILITY_ENABLED"])

    before_amount, after_amount = _max_amount(before), _max_amount(after)
    if (
        metadata.effect == "financial"
        and before_amount is not None
        and after_amount is not None
        and after_amount > before_amount
    ):
        return CapabilityChange(ChangeSeverity.CRITICAL, ["FINANCIAL_AUTHORITY_INCREASED"])
    if before != after:
        return CapabilityChange(ChangeSeverity.MATERIAL, ["CAPABILITY_CONFIGURATION_CHANGED"])
    deployment_changed = (
        version_diff.model.changed or version_diff.prompt.changed or version_diff.code.changed
    )
    if metadata.sensitive and deployment_changed:
        return CapabilityChange(
            ChangeSeverity.MATERIAL,
            ["SENSITIVE_CAPABILITY_DEPLOYMENT_CHANGED"],
        )
    return CapabilityChange(ChangeSeverity.SAFE, ["CAPABILITY_UNCHANGED"])
