import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.repositories import organization as organizations
from app.db.session import get_db
from app.schemas.organization_policy import OrganizationPolicyRead, OrganizationPolicyUpsert
from app.services import organization_policy as policies

router = APIRouter(prefix="/organizations/{organization_id}/policy", tags=["organization-policy"])


@router.get("", response_model=OrganizationPolicyRead)
def get_policy(organization_id: uuid.UUID, db: Session = Depends(get_db)) -> OrganizationPolicyRead:
    if organizations.get(db, organization_id) is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    policy = policies.get(db, organization_id)
    if policy is None:
        raise HTTPException(status_code=404, detail="Organization policy not found")
    return policy


@router.put("", response_model=OrganizationPolicyRead)
def upsert_policy(
    organization_id: uuid.UUID,
    payload: OrganizationPolicyUpsert,
    db: Session = Depends(get_db),
) -> OrganizationPolicyRead:
    if organizations.get(db, organization_id) is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    return policies.upsert(db, organization_id, payload)
