from datetime import UTC, datetime
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import get_settings

settings = get_settings()
PROCESS_STARTED_AT = datetime.now(UTC).isoformat()
RUNTIME_COMMIT = os.getenv("RENDER_GIT_COMMIT", "local")
# Sprint 8E: source-level no-op marker for the mandatory post-provider restart boundary.

app = FastAPI(
    title=settings.app_name,
    description="Sellora modular monolith SaaS CRM foundation API.",
    version="0.1.0",
    openapi_url=f"{settings.api_v1_prefix}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/health", tags=["Health"])
def health() -> dict[str, str]:
    """Return non-secret deployment identity for release-gate evidence."""

    return {
        "status": "ok",
        "runtime_commit": RUNTIME_COMMIT,
        "process_started_at": PROCESS_STARTED_AT,
    }
