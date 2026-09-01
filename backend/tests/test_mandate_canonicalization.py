import pytest

from app.schemas.mandate import ProcurementIntent
from app.services.intent_extractor import MockIntentExtractor
from app.services.mandate_canonicalization import canonicalize_mandate


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("purchase", "purchase"),
        ("buy", "purchase"),
        ("BUY", "purchase"),
        (" get ", "purchase"),
        ("Procure", "purchase"),
        ("purchasing", "purchase"),
    ],
)
def test_action_aliases_are_explicit_and_case_insensitive(raw: str, expected: str) -> None:
    result = canonicalize_mandate(ProcurementIntent(action_type=raw))
    assert result.candidate.action_type == expected
    assert result.issues == []


@pytest.mark.parametrize(
    "raw",
    ["gpu", "gpus", "GPUs", "graphics card", "graphics cards", "graphics processing units"],
)
def test_gpu_aliases_are_canonicalized(raw: str) -> None:
    result = canonicalize_mandate(ProcurementIntent(item_category=raw))
    assert result.candidate.item_category == "gpu"
    assert result.issues == []


def test_unknown_critical_values_are_preserved_and_reported() -> None:
    result = canonicalize_mandate(
        ProcurementIntent(action_type="acquire", item_category="accelerator")
    )
    assert result.candidate.action_type == "acquire"
    assert result.candidate.item_category == "accelerator"
    assert [(issue.field, issue.code) for issue in result.issues] == [
        ("action_type", "UNSUPPORTED_ACTION_TYPE"),
        ("item_category", "UNSUPPORTED_ITEM_CATEGORY"),
    ]


def test_constraints_and_other_fields_are_not_broadened() -> None:
    candidate = ProcurementIntent(
        action_type=" get ",
        item_category=" GPUs ",
        quantity_max=12,
        max_amount=14_500,
        currency="usd",
        vendor_policy="approved_only",
        approved_vendors=["CDW"],
        purpose="for our ML researchers",
    )
    result = canonicalize_mandate(candidate).candidate
    assert result.quantity_max == 12
    assert result.max_amount == 14_500
    assert result.currency == "USD"
    assert result.vendor_policy == "approved_only"
    assert result.approved_vendors == ["CDW"]
    assert result.purpose == "for our ML researchers"


def test_mock_provider_output_also_passes_through_canonicalization() -> None:
    raw = MockIntentExtractor(
        ProcurementIntent(action_type="BUY", item_category="graphics card", max_amount=14_500)
    ).extract("ignored")
    result = canonicalize_mandate(raw)
    assert raw.action_type == "BUY"
    assert raw.item_category == "graphics card"
    assert result.candidate.action_type == "purchase"
    assert result.candidate.item_category == "gpu"
