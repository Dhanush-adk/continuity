import json
import re
from typing import Protocol

from app.core.config import settings
from app.schemas.mandate import ProcurementIntent


class IntentExtractor(Protocol):
    def extract(self, text: str) -> ProcurementIntent: ...


class MockIntentExtractor:
    """Deterministic development extractor; intentionally leaves unknown limits null."""

    def __init__(self, candidate: ProcurementIntent | None = None) -> None:
        self.candidate = candidate

    def extract(self, text: str) -> ProcurementIntent:
        if self.candidate is not None:
            return self.candidate
        lowered = text.lower()
        quantity = _first_int(r"\b(\d+)\s+gpus?\b", lowered)
        amount = _first_int(r"(?:under|maximum|max(?:imum)?)[^$]*\$?([\d,]+)", lowered)
        return ProcurementIntent(
            action_type="purchase"
            if any(word in lowered for word in ("purchase", "buy"))
            else None,
            item_category="gpu" if "gpu" in lowered else None,
            quantity_max=quantity,
            max_amount=amount,
            currency="USD" if "$" in text or "usd" in lowered else None,
            vendor_policy="approved_only" if "approved vendor" in lowered else "unspecified",
            purpose="ML team" if "ml team" in lowered else None,
        )


class GeminiIntentExtractor:
    def __init__(self, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model

    def extract(self, text: str) -> ProcurementIntent:
        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:  # pragma: no cover - exercised only with Gemini configured
            raise RuntimeError("google-genai is required for the Gemini intent extractor") from exc

        prompt = (
            "Extract a procurement mandate candidate from the user text. Return only the schema. "
            "Never invent numeric limits, vendors, currencies, categories, or purpose; use null or "
            "'unspecified' when absent or ambiguous. "
            "This is extraction only, not authorization.\n\n"
            f"User text: {text}"
        )
        client = genai.Client(api_key=self.api_key)
        response = client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ProcurementIntent,
            ),
        )
        candidate = response.parsed
        if candidate is None:
            if not response.text:
                raise ValueError("Gemini returned no structured intent")
            candidate = json.loads(response.text)
        return validate_candidate(candidate)


def _first_int(pattern: str, text: str) -> int | None:
    match = re.search(pattern, text, flags=re.IGNORECASE)
    return int(match.group(1).replace(",", "")) if match else None


def validate_candidate(candidate: object) -> ProcurementIntent:
    """Apply local Pydantic validation to all provider output before persistence."""
    if isinstance(candidate, ProcurementIntent):
        return candidate
    return ProcurementIntent.model_validate(candidate)


def get_intent_extractor() -> IntentExtractor:
    if settings.intent_extractor == "mock":
        return MockIntentExtractor()
    if settings.gemini_api_key is None:
        raise RuntimeError("GEMINI_API_KEY is required when INTENT_EXTRACTOR=gemini")
    return GeminiIntentExtractor(settings.gemini_api_key, settings.gemini_model)
