#!/usr/bin/env python3
"""Fail build/startup when Sprint 8B routes are absent from the packaged API."""
from __future__ import annotations

from app.api.v1.router import api_router

REQUIRED_ROUTES = {
    ("GET", "/onboarding/status"),
    ("POST", "/workspaces/demo"),
    ("PATCH", "/workspaces/demo/deactivate"),
}


def packaged_routes() -> set[tuple[str, str]]:
    found: set[tuple[str, str]] = set()
    for route in api_router.routes:
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", set()) or set()
        if not path:
            continue
        for method in methods:
            found.add((str(method).upper(), str(path)))
    return found


def main() -> None:
    found = packaged_routes()
    missing = sorted(REQUIRED_ROUTES - found)
    if missing:
        rendered = ", ".join(f"{method} {path}" for method, path in missing)
        raise SystemExit(f"Sprint 8B route verification failed: missing {rendered}")
    rendered = ", ".join(f"{method} {path}" for method, path in sorted(REQUIRED_ROUTES))
    print(f"Sprint 8B routes verified: {rendered}")


if __name__ == "__main__":
    main()
