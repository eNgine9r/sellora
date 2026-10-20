from contextlib import asynccontextmanager, suppress
from datetime import UTC, datetime
import asyncio
import os
import time
from urllib.parse import urlsplit

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.runtime_health import LOOP_STATE, monitor_event_loop, worker_snapshot, db_snapshot
from app.database.session import engine
from app.integrations.meta_instagram.runtime_worker import run_instagram_webhook_worker, webhook_worker_enabled

settings = get_settings()
PROCESS_STARTED_AT = datetime.now(UTC).isoformat()
RUNTIME_COMMIT = os.getenv("RENDER_GIT_COMMIT", "local")
# Sprint 8E: source-level no-op marker for the mandatory post-provider restart boundary.


@asynccontextmanager
async def lifespan(app: FastAPI):
    stop_event = asyncio.Event()
    monitor_task = asyncio.create_task(monitor_event_loop(), name="event-loop-monitor")
    worker_task: asyncio.Task[None] | None = None
    if settings.meta_instagram_webhook_processing_enabled and webhook_worker_enabled():
        worker_task = asyncio.create_task(run_instagram_webhook_worker(stop_event), name="instagram-webhook-worker")
    app.state.instagram_webhook_worker_task = worker_task
    app.state.instagram_webhook_worker_running = worker_task is not None
    try:
        yield
    finally:
        monitor_task.cancel()
        with suppress(asyncio.CancelledError):
            await monitor_task
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
    for origin in origins:
        parsed = urlsplit(origin)
        if (
            parsed.scheme not in ("https", "http")
            or not parsed.hostname
            or origin != f"{parsed.scheme}://{parsed.netloc}"
            or parsed.username is not None
            or parsed.password is not None
            or "*" in origin
            or (settings.environment == "production" and parsed.scheme != "https")
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
async def health() -> dict[str, object]:
    """Return non-secret deployment identity for release-gate evidence."""

    return {
        "status": "ok",
        "runtime_commit": RUNTIME_COMMIT,
        "process_started_at": PROCESS_STARTED_AT,
        "meta_webhook_worker_enabled": webhook_worker_enabled(),
        "meta_webhook_processing_enabled": settings.meta_instagram_webhook_processing_enabled,
        "meta_webhook_worker_running": bool(getattr(app.state, "instagram_webhook_worker_task", None) and not app.state.instagram_webhook_worker_task.done()),
    }


@app.get("/health/live", tags=["Health"])
async def liveness() -> dict[str, str]:
    # No DB or thread-pool dependency: remains responsive during worker stalls.
    return {"status": "ok"}


@app.get("/health/ready", tags=["Health"])
async def readiness(response: Response) -> dict[str, object]:
    task = getattr(app.state, "instagram_webhook_worker_task", None)
    required = settings.meta_instagram_webhook_processing_enabled and webhook_worker_enabled()
    state = worker_snapshot()
    ready = not required or bool(task and not task.done() and not state["stalled"])
    response.status_code = 200 if ready else 503
    checked_out = getattr(engine.pool, "checkedout", None)
    return {"status": "ok" if ready else "degraded",
            "worker": state, "event_loop_lag_seconds": LOOP_STATE["lag_seconds"],
            "db": db_snapshot() | {"checked_out": checked_out() if checked_out else None,
                                   "pool_wait_limit_seconds": 5},
            "http": getattr(app.state, "last_http", {})}


@app.middleware("http")
async def request_timing(request, call_next):
    started = time.monotonic()
    response = await call_next(request)
    app.state.last_http = {"response_seconds": round(time.monotonic() - started, 3),
                           "status_code": response.status_code,
                           "completed_at": datetime.now(UTC).isoformat()}
    return response
