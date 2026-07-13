#!/usr/bin/env python3
"""Fail build/startup when Sprint 8B routes are absent from the packaged API."""
from __future__ import annotations

import inspect
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

import fastapi
from fastapi import APIRouter
import app as app_package
import app.main as main_module
import app.api.v1.router as central_router_module
from app.api.v1.auth import router as auth_router
from app.api.v1.onboarding import router as onboarding_router
from app.api.v1.workspaces import router as workspaces_router
from app.main import app

REQUIRED_ROUTES = {
    ("GET", "/api/v1/onboarding/status"),
    ("POST", "/api/v1/workspaces/demo"),
    ("PATCH", "/api/v1/workspaces/demo/deactivate"),
}


def router_routes(router, *, prefix: str = "") -> set[tuple[str, str]]:
    found: set[tuple[str, str]] = set()
    for route in router.routes:
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", set()) or set()
        if not path:
            continue
        if not methods:
            found.add(("MOUNT", f"{prefix}{path}"))
        for method in methods:
            found.add((str(method).upper(), f"{prefix}{path}"))
    return found


def render_routes(routes: set[tuple[str, str]]) -> str:
    return "; ".join(f"{method} {path}" for method, path in sorted(routes)) or "none"


def include_router_probe() -> str:
    child = APIRouter()

    @child.get("/probe")
    def probe_endpoint() -> dict[str, bool]:
        return {"ok": True}

    parent = APIRouter()
    returned = parent.include_router(child)
    return (
        f"fastapi_version={getattr(fastapi, '__version__', 'unknown')}; "
        f"include_router_signature={inspect.signature(parent.include_router)}; "
        f"include_router_return_type={type(returned).__name__}; "
        f"probe_parent_routes={render_routes(router_routes(parent))}; "
        f"probe_return_routes={render_routes(router_routes(returned)) if hasattr(returned, 'routes') else 'n/a'}"
    )


def main() -> None:
    child = {
        "auth": router_routes(auth_router),
        "onboarding": router_routes(onboarding_router),
        "workspaces": router_routes(workspaces_router),
    }
    central = router_routes(central_router_module.api_router)
    packaged = router_routes(app)
    missing = sorted(REQUIRED_ROUTES - packaged)
    diagnostics = (
        f"backend_root={BACKEND_ROOT}; "
        f"app_package={getattr(app_package, '__file__', None)}; "
        f"main_module={getattr(main_module, '__file__', None)}; "
        f"central_module={getattr(central_router_module, '__file__', None)}; "
        f"child_auth={render_routes(child['auth'])}; "
        f"child_onboarding={render_routes(child['onboarding'])}; "
        f"child_workspaces={render_routes(child['workspaces'])}; "
        f"central_routes={render_routes(central)}; "
        f"app_routes={render_routes(packaged)}; "
        f"{include_router_probe()}"
    )
    if missing:
        rendered = ", ".join(f"{method} {path}" for method, path in missing)
        raise SystemExit(f"Sprint 8B route verification failed: missing {rendered}. {diagnostics}")
    rendered = ", ".join(f"{method} {path}" for method, path in sorted(REQUIRED_ROUTES))
    print(f"Sprint 8B routes verified: {rendered}")
    print(diagnostics)


if __name__ == "__main__":
    main()
