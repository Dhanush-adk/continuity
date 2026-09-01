import uuid

from sqlalchemy.orm import Session

from app.db.repositories import mandate as mandates
from app.models.mandate import Mandate, MandateStatus
from app.schemas.mandate import MandateExtractRequest
from app.services.intent_extractor import IntentExtractor
from app.services.mandate_canonicalization import canonicalize_mandate


def extract_and_create(
    db: Session, payload: MandateExtractRequest, extractor: IntentExtractor
) -> Mandate:
    candidate = extractor.extract(payload.text)
    canonical = canonicalize_mandate(candidate)
    mandate = Mandate(
        organization_id=payload.organization_id,
        requester_id=payload.requester_id,
        agent_id=payload.agent_id,
        raw_intent=payload.text,
        raw_extraction=candidate.model_dump(mode="json"),
        structured_intent=canonical.candidate.model_dump(mode="json"),
        canonicalization_issues=[issue.model_dump(mode="json") for issue in canonical.issues],
        status=MandateStatus.DRAFT,
        expires_at=payload.expires_at,
    )
    return mandates.save(db, mandate)


def get(db: Session, mandate_id: uuid.UUID) -> Mandate | None:
    return mandates.get(db, mandate_id)


def activate(db: Session, mandate: Mandate) -> Mandate:
    if mandate.status != MandateStatus.DRAFT:
        raise ValueError("Only DRAFT mandates can be activated")
    if mandate.canonicalization_issues:
        raise ValueError(
            "Mandate requires canonicalization: "
            + ", ".join(issue["code"] for issue in mandate.canonicalization_issues)
        )
    mandate.status = MandateStatus.ACTIVE
    return mandates.save(db, mandate)
