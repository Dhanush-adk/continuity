from dataclasses import dataclass

from app.schemas.mandate import CanonicalizationIssue, ProcurementIntent

ACTION_ALIASES = {
    "purchase": "purchase",
    "buy": "purchase",
    "get": "purchase",
    "procure": "purchase",
    "purchasing": "purchase",
}
CATEGORY_ALIASES = {
    "gpu": "gpu",
    "gpus": "gpu",
    "graphics card": "gpu",
    "graphics cards": "gpu",
    "graphics processing unit": "gpu",
    "graphics processing units": "gpu",
}


@dataclass(frozen=True)
class CanonicalizationResult:
    candidate: ProcurementIntent
    issues: list[CanonicalizationIssue]


def _normalized(value: str) -> str:
    return " ".join(value.strip().casefold().split())


def canonicalize_mandate(candidate: ProcurementIntent) -> CanonicalizationResult:
    """Canonicalize only explicit aliases; preserve unknown values and report issues."""
    issues: list[CanonicalizationIssue] = []
    action = candidate.action_type
    if action is not None:
        key = _normalized(action)
        action = ACTION_ALIASES.get(key)
        if action is None:
            action = candidate.action_type.strip()
            issues.append(
                CanonicalizationIssue(
                    field="action_type", code="UNSUPPORTED_ACTION_TYPE", value=action
                )
            )
    category = candidate.item_category
    if category is not None:
        key = _normalized(category)
        category = CATEGORY_ALIASES.get(key)
        if category is None:
            category = candidate.item_category.strip()
            issues.append(
                CanonicalizationIssue(
                    field="item_category", code="UNSUPPORTED_ITEM_CATEGORY", value=category
                )
            )
    currency = candidate.currency.upper() if candidate.currency is not None else None
    return CanonicalizationResult(
        candidate=candidate.model_copy(
            update={"action_type": action, "item_category": category, "currency": currency}
        ),
        issues=issues,
    )
