from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.db.repositories import (
    agent as agents,
)
from app.db.repositories import (
    agent_version as versions,
)
from app.db.repositories import (
    authorization_decision as decisions,
)
from app.db.repositories import (
    capability_trust as trusts,
)
from app.db.repositories import (
    mandate as mandates,
)
from app.db.repositories import (
    organization as organizations,
)
from app.db.repositories import (
    organization_policy as policies,
)
from app.models.authorization_decision import AuthorizationDecision, AuthorizationOutcome
from app.models.capability_trust import CapabilityTrustStatus
from app.models.mandate import MandateStatus
from app.schemas.authorization import (
    AuthorizationCheck,
    AuthorizationChecks,
    AuthorizationRequest,
    AuthorizationResponse,
    ReasonDetail,
)


class AuthorizationNotFoundError(ValueError):
    pass


def _check(
    status: str, *, trust_status: str | None = None, envelope: dict[str, Any] | None = None
) -> AuthorizationCheck:
    return AuthorizationCheck(status=status, trust_status=trust_status, trusted_envelope=envelope)


def _reason(code: str, expected: Any | None = None, actual: Any | None = None) -> ReasonDetail:
    return ReasonDetail(code=code, expected=expected, actual=actual)


def _expired(expires_at: datetime | None) -> bool:
    if expires_at is None:
        return False
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    return expires_at <= datetime.now(UTC)


def authorize(db: Session, payload: AuthorizationRequest) -> AuthorizationResponse:
    """Evaluate authorization deterministically and persist an immutable audit snapshot."""
    organization = organizations.get(db, payload.organization_id)
    agent = agents.get(db, payload.agent_id)
    mandate = mandates.get(db, payload.mandate_id)
    if organization is None or agent is None or mandate is None:
        raise AuthorizationNotFoundError("Organization, agent, or mandate not found")
    version = versions.get(db, payload.agent_id, payload.agent_version_id)
    if version is None:
        raise AuthorizationNotFoundError("Agent version not found")

    reasons: list[ReasonDetail] = []
    deployment_ok = agent.organization_id == organization.id and version.agent_id == agent.id
    if not deployment_ok:
        reasons.append(_reason("DEPLOYMENT_ORGANIZATION_MISMATCH"))
    deployment_check = _check("PASS" if deployment_ok else "FAIL")

    mandate_ok = True
    if mandate.organization_id != organization.id:
        mandate_ok = False
        reasons.append(_reason("MANDATE_ORGANIZATION_MISMATCH"))
    if mandate.agent_id is not None and mandate.agent_id != agent.id:
        mandate_ok = False
        reasons.append(_reason("MANDATE_AGENT_MISMATCH"))
    if mandate.status != MandateStatus.ACTIVE:
        mandate_ok = False
        reasons.append(
            _reason("MANDATE_NOT_ACTIVE", MandateStatus.ACTIVE.value, mandate.status.value)
        )
    if _expired(mandate.expires_at):
        mandate_ok = False
        reasons.append(_reason("MANDATE_EXPIRED"))

    intent = mandate.structured_intent
    action = payload.action
    _mandate_constraints(intent, action, reasons)
    if any(reason.code.startswith("MANDATE_") for reason in reasons):
        mandate_ok = False
    mandate_check = _check("PASS" if mandate_ok else "FAIL")

    trust = trusts.get_for_version(db, version.id, payload.capability)
    capability_status = "PASS"
    if trust is None:
        capability_status = "FAIL"
        reasons.append(_reason("CAPABILITY_TRUST_NOT_FOUND", actual=payload.capability))
        trust_snapshot: dict[str, Any] = {}
    else:
        trust_snapshot = {
            "status": trust.status.value,
            "autonomy_constraints": trust.autonomy_constraints,
            "reason_codes": trust.reason_codes,
            "inherited_from_version_id": str(trust.inherited_from_version_id)
            if trust.inherited_from_version_id
            else None,
        }
        if trust.status == CapabilityTrustStatus.UNTRUSTED:
            capability_status = "FAIL"
            reasons.append(_reason("CAPABILITY_UNTRUSTED", actual=payload.capability))
        else:
            max_amount = trust.autonomy_constraints.get("max_amount")
            if isinstance(max_amount, (int, float)) and action.amount > max_amount:
                capability_status = "REVIEW"
                reasons.append(_reason("TRUSTED_ENVELOPE_EXCEEDED", max_amount, action.amount))
    capability_check = _check(
        capability_status,
        trust_status=trust.status.value if trust else None,
        envelope=trust.autonomy_constraints if trust else None,
    )

    policy = policies.get_for_organization(db, organization.id)
    policy_status = "PASS"
    policy_snapshot: dict[str, Any] = {}
    if policy is not None:
        policy_snapshot = {
            "approved_vendors": policy.approved_vendors,
            "approval_thresholds": policy.approval_thresholds,
            "hard_payment_limit": policy.hard_payment_limit,
        }
        if policy.approved_vendors and action.vendor not in policy.approved_vendors:
            policy_status = "FAIL"
            reasons.append(_reason("VENDOR_NOT_APPROVED", actual=action.vendor))
        if policy.hard_payment_limit is not None and action.amount > policy.hard_payment_limit:
            policy_status = "FAIL"
            reasons.append(
                _reason(
                    "ORGANIZATION_HARD_LIMIT_EXCEEDED", policy.hard_payment_limit, action.amount
                )
            )
        if (
            any(
                action.amount >= threshold.get("amount_gte", float("inf"))
                and threshold.get("action") == "REVIEW"
                for threshold in policy.approval_thresholds
            )
            and policy_status != "FAIL"
        ):
            policy_status = "REVIEW"
            reasons.append(_reason("ORGANIZATION_APPROVAL_REQUIRED", actual=action.amount))
    policy_check = _check(policy_status)

    checks = AuthorizationChecks(
        deployment=deployment_check,
        capability=capability_check,
        mandate=mandate_check,
        organization_policy=policy_check,
    )
    decision = _decision_for(checks)
    record = AuthorizationDecision(
        organization_id=organization.id,
        agent_id=agent.id,
        agent_version_id=version.id,
        mandate_id=mandate.id,
        capability_name=payload.capability,
        proposed_action=action.model_dump(mode="json"),
        decision=decision,
        reason_codes=[reason.model_dump(mode="json") for reason in reasons],
        capability_trust_snapshot=trust_snapshot,
        mandate_snapshot={
            "raw_intent": mandate.raw_intent,
            "raw_extraction": mandate.raw_extraction,
            "status": mandate.status.value,
            "structured_intent": intent,
            "canonicalization_issues": mandate.canonicalization_issues,
            "expires_at": mandate.expires_at.isoformat() if mandate.expires_at else None,
        },
        policy_snapshot=policy_snapshot,
    )
    record = decisions.add(db, record)
    return AuthorizationResponse(
        decision_id=record.id,
        decision=decision,
        checks=checks,
        reasons=reasons,
        created_at=record.created_at,
    )


def _mandate_constraints(intent: dict[str, Any], action: Any, reasons: list[ReasonDetail]) -> None:
    expected_action = intent.get("action_type")
    if expected_action is None or action.action_type != expected_action:
        reasons.append(_reason("MANDATE_ACTION_TYPE_MISMATCH", expected_action, action.action_type))
    expected_category = intent.get("item_category")
    if expected_category is None or action.item_category != expected_category:
        reasons.append(
            _reason("MANDATE_CATEGORY_MISMATCH", expected_category, action.item_category)
        )
    quantity_max = intent.get("quantity_max")
    if quantity_max is None:
        reasons.append(_reason("MANDATE_QUANTITY_UNSPECIFIED"))
    elif action.quantity > quantity_max:
        reasons.append(_reason("MANDATE_QUANTITY_EXCEEDED", quantity_max, action.quantity))
    max_amount = intent.get("max_amount")
    if max_amount is None:
        reasons.append(_reason("MANDATE_AMOUNT_UNSPECIFIED"))
    elif action.amount > max_amount:
        reasons.append(_reason("MANDATE_AMOUNT_EXCEEDED", max_amount, action.amount))
    expected_currency = intent.get("currency")
    if expected_currency is None or action.currency != expected_currency:
        reasons.append(_reason("MANDATE_CURRENCY_MISMATCH", expected_currency, action.currency))
    vendors = intent.get("approved_vendors")
    if intent.get("vendor_policy") == "approved_only" and vendors and action.vendor not in vendors:
        reasons.append(_reason("MANDATE_VENDOR_NOT_APPROVED", vendors, action.vendor))
    expected_purpose = intent.get("purpose")
    if expected_purpose is not None and action.purpose != expected_purpose:
        reasons.append(_reason("MANDATE_PURPOSE_MISMATCH", expected_purpose, action.purpose))


def _decision_for(checks: AuthorizationChecks) -> AuthorizationOutcome:
    states = [
        checks.deployment.status,
        checks.capability.status,
        checks.mandate.status,
        checks.organization_policy.status,
    ]
    if "FAIL" in states:
        return AuthorizationOutcome.DENY
    if "REVIEW" in states:
        return AuthorizationOutcome.REVIEW
    return AuthorizationOutcome.ALLOW
