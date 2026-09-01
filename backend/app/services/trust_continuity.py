import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.db.repositories import capability_trust as trusts
from app.models.agent_version import AgentVersion
from app.models.capability_trust import CapabilityTrust, CapabilityTrustStatus, ContinuityAction
from app.schemas.agent_version import VersionDiff
from app.schemas.capability_trust import (
    CapabilityContinuityResult,
    ContinuityEvaluationResponse,
    ContinuitySummary,
    ReauthorizationRequest,
)
from app.services.capability_metadata import metadata_for
from app.services.change_classifier import ChangeSeverity, classify_capability_change


def _declared_constraints(version: AgentVersion, capability_name: str) -> dict[str, Any]:
    capability = version.capability_manifest.get(capability_name, {})
    if not isinstance(capability, dict):
        return {}
    constraints = capability.get("constraints", {})
    return constraints if isinstance(constraints, dict) else {}


def _persist(
    db: Session,
    *,
    version: AgentVersion,
    capability_name: str,
    status: CapabilityTrustStatus,
    action: ContinuityAction,
    inherited_from_version_id: uuid.UUID | None,
    constraints: dict[str, Any],
    reasons: list[str],
) -> CapabilityTrust:
    existing = trusts.get_for_version(db, version.id, capability_name)
    if existing is not None and existing.explicitly_reauthorized:
        return existing
    trust = existing or CapabilityTrust(
        agent_version_id=version.id,
        capability_name=capability_name,
    )
    trust.status = status
    trust.continuity_action = action
    trust.inherited_from_version_id = inherited_from_version_id
    trust.autonomy_constraints = constraints
    trust.reason_codes = reasons
    trust.explicitly_reauthorized = False
    trust.reauthorized_at = None
    trust.reauthorization_reason = None
    return trusts.save(db, trust)


def _result(trust: CapabilityTrust, severity: ChangeSeverity) -> CapabilityContinuityResult:
    return CapabilityContinuityResult(
        capability_name=trust.capability_name,
        decision=trust.continuity_action,
        resulting_status=trust.status,
        change_severity=severity,
        inherited_from_version_id=trust.inherited_from_version_id,
        autonomy_constraints=trust.autonomy_constraints,
        reasons=trust.reason_codes,
        explicitly_reauthorized=trust.explicitly_reauthorized,
    )


def evaluate_trust_continuity(
    db: Session,
    previous_version: AgentVersion,
    new_version: AgentVersion,
    version_diff: VersionDiff,
) -> ContinuityEvaluationResponse:
    """Derive capability-scoped continuity records using explicit rules."""
    results: list[CapabilityContinuityResult] = []
    for capability_name in sorted(new_version.capability_manifest):
        change = classify_capability_change(
            previous_version,
            new_version,
            version_diff,
            capability_name,
        )
        previous_trust = trusts.get_for_version(db, previous_version.id, capability_name)
        metadata = metadata_for(capability_name)

        if previous_trust is None:
            trust = _persist(
                db,
                version=new_version,
                capability_name=capability_name,
                status=CapabilityTrustStatus.UNTRUSTED,
                action=ContinuityAction.REAUTHORIZE,
                inherited_from_version_id=None,
                constraints={},
                reasons=[*change.reason_codes, "NO_PRIOR_CAPABILITY_TRUST"],
            )
        elif metadata.effect == "unknown":
            trust = _persist(
                db,
                version=new_version,
                capability_name=capability_name,
                status=CapabilityTrustStatus.UNTRUSTED,
                action=ContinuityAction.REAUTHORIZE,
                inherited_from_version_id=None,
                constraints={},
                reasons=["UNKNOWN_CAPABILITY_METADATA"],
            )
        elif change.severity == ChangeSeverity.SAFE:
            trust = _persist(
                db,
                version=new_version,
                capability_name=capability_name,
                status=previous_trust.status,
                action=ContinuityAction.INHERIT,
                inherited_from_version_id=previous_version.id,
                constraints=previous_trust.autonomy_constraints,
                reasons=change.reason_codes,
            )
        elif (
            change.severity == ChangeSeverity.CRITICAL
            and "CAPABILITY_ENABLED" in change.reason_codes
        ):
            trust = _persist(
                db,
                version=new_version,
                capability_name=capability_name,
                status=CapabilityTrustStatus.UNTRUSTED,
                action=ContinuityAction.REAUTHORIZE,
                inherited_from_version_id=None,
                constraints={},
                reasons=change.reason_codes,
            )
        else:
            trust = _persist(
                db,
                version=new_version,
                capability_name=capability_name,
                status=CapabilityTrustStatus.LIMITED,
                action=ContinuityAction.RESTRICT,
                inherited_from_version_id=previous_version.id,
                constraints=previous_trust.autonomy_constraints,
                reasons=[*change.reason_codes, "PREVIOUS_TRUST_ENVELOPE_RETAINED"],
            )
        results.append(_result(trust, change.severity))

    summary = ContinuitySummary(
        inherited=sum(result.decision == ContinuityAction.INHERIT for result in results),
        restricted=sum(result.decision == ContinuityAction.RESTRICT for result in results),
        reauthorization_required=sum(
            result.decision == ContinuityAction.REAUTHORIZE for result in results
        ),
    )
    return ContinuityEvaluationResponse(
        agent_id=new_version.agent_id,
        from_version=previous_version.version,
        to_version=new_version.version,
        summary=summary,
        capabilities=results,
    )


def explicitly_reauthorize(
    db: Session,
    version: AgentVersion,
    capability_name: str,
    request: ReauthorizationRequest,
) -> CapabilityTrust:
    if capability_name not in version.capability_manifest:
        raise ValueError("Capability is not declared by this agent version")
    trust = trusts.get_for_version(db, version.id, capability_name)
    if trust is None:
        trust = CapabilityTrust(agent_version_id=version.id, capability_name=capability_name)
    trust.status = CapabilityTrustStatus.TRUSTED
    trust.continuity_action = ContinuityAction.REAUTHORIZE
    trust.inherited_from_version_id = None
    trust.autonomy_constraints = request.autonomy_constraints
    trust.reason_codes = ["EXPLICIT_REAUTHORIZATION"]
    trust.explicitly_reauthorized = True
    trust.reauthorized_at = datetime.now(UTC)
    trust.reauthorization_reason = request.reason
    return trusts.save(db, trust)
