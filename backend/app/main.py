from fastapi import FastAPI

from app.api.agents import router as agents_router
from app.api.authorization import router as authorization_router
from app.api.mandates import router as mandates_router
from app.api.organization_policies import router as organization_policies_router
from app.api.organizations import router as organizations_router
from app.core.logging import configure_logging

configure_logging()
app = FastAPI(title="Continuity", version="0.1.0")
app.include_router(organizations_router)
app.include_router(agents_router)
app.include_router(mandates_router)
app.include_router(organization_policies_router)
app.include_router(authorization_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
