#!/usr/bin/env python3
"""Fail build/startup when Sprint 8B routes are absent from the packaged API.

FastAPI 0.137+ preserves nested APIRouter instances instead of flattening them
into ``app.routes``. Generated OpenAPI paths are the stable packaged API source
of truth across the supported FastAPI versions.
"""
from __future__ import annotations

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

import fastapi
from app.main import app

REQUIRED_ROUTES = {
    ("GET", "/api/v1/onboarding/status"),
    ("POST", "/api/v1/workspaces/demo"),
    ("PATCH", "/api/v1/workspaces/demo/deactivate"),
}


def packaged_routes() -> set[tuple[str, str]]:
    schema = app.openapi()
    found: set[tuple[str, str]] = set()
    for path, operations in schema.get("paths", {}).items():
        if not isinstance(operations, dict):
            continue
        for method in operations:
            normalized = str(method).upper()
            if normalized in {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS", "TRACE"}:
                found.add((normalized, str(path)))
    return found


def main() -> None:
    found = packaged_routes()
    missing = sorted(REQUIRED_ROUTES - found)
    if missing:
        rendered = ", ".join(f"{method} {path}" for method, path in missing)
        relevant = "; ".join(
            f"{method} {path}"
            for method, path in sorted(found)
            if "onboarding" in path or "workspaces/demo" in path
        )
        raise SystemExit(
            f"Sprint 8B route verification failed with FastAPI {fastapi.__version__}: "
            f"missing {rendered}. Available relevant routes: {relevant or 'none'}"
        )
    rendered = ", ".join(f"{method} {path}" for method, path in sorted(REQUIRED_ROUTES))
    print(f"Sprint 8B routes verified with FastAPI {fastapi.__version__}: {rendered}")


if __name__ == "__main__":
    main()
