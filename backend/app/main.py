from contextlib import asynccontextmanager, suppress
from datetime import UTC, datetime
import asyncio
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.integrations.meta_instagram.runtime_worker import run_instagram_webhook_worker, webhook_worker_enabled

settings = get_settings()
PROCESS_STARTED_AT = datetime.now(UTC).isoformat()
RUNTIME_COMMIT = os.getenv("RENDER_GIT_COMMIT", "local")
# Sprint 8E: source-level no-op marker for the mandatory post-provider restart boundary.


@asynccontextmanager
async def lifespan(app: FastAPI):
    stop_event = asyncio.Event()
    worker_task: asyncio.Task[None] | None = None
    if settings.meta_instagram_webhook_processing_enabled and webhook_worker_enabled():
        worker_task = asyncio.create_task(run_instagram_webhook_worker(stop_event), name="instagram-webhook-worker")
    app.state.instagram_webhook_worker_running = worker_task is not None
    try:
        yield
    finally:
        if worker_task is not None:
            stop_event.set()
            worker_task.cancel()
            with suppress(asyncio.CancelledError):
                await worker_task
        app.state.instagram_webhook_worker_running = False


app = FastAPI(
    title=settings.app_name,
    description="Sellora modular monolith SaaS CRM foundation API.",
    version="0.1.0",
    openapi_url=f"{settings.api_v1_prefix}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

def allowed_cors_origins() -> list[str]:
    """Permit explicitly trusted storefronts; no credentialed wildcard CORS."""
    configured = os.getenv("SELLORA_CORS_ALLOWED_ORIGINS", "")
    origins = [
        origin.strip().rstrip("/")
        for origin in configured.split(",")
        if origin.strip()
    ] if configured.strip() else ["https://sellora-web-staging.vercel.app"]
    if settings.environment != "production":
        origins.extend(("http://localhost:3000", "http://127.0.0.1:3000"))
    # Misconfiguration must fail closed, rather than silently reopening CORS.
    if any(
        not origin.startswith(("https://", "http://"))
        or "*" in origin
        or (settings.environment == "production" and not origin.startswith("https://"))
        or "/" in origin.split("://", 1)[1]
        for origin in origins
    ):
        raise ValueError("SELLORA_CORS_ALLOWED_ORIGINS must list trusted origins only")
    return sorted(set(origins))


app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_cors_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/health", tags=["Health"])
def health() -> dict[str, object]:
    """Return non-secret deployment identity for release-gate evidence."""

    return {
        "status": "ok",
        "runtime_commit": RUNTIME_COMMIT,
        "process_started_at": PROCESS_STARTED_AT,
        "meta_webhook_worker_enabled": webhook_worker_enabled(),
        "meta_webhook_processing_enabled": settings.meta_instagram_webhook_processing_enabled,
        "meta_webhook_worker_running": bool(getattr(app.state, "instagram_webhook_worker_running", False)),
    }
