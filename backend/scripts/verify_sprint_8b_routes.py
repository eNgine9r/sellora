#!/usr/bin/env python3
"""Fail build/startup when Sprint 8B routes are absent from the packaged API."""
from __future__ import annotations

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

import app as app_package
import app.main as main_module
from app.main import app

REQUIRED_ROUTES = {
    ("GET", "/api/v1/onboarding/status"),
    ("POST", "/api/v1/workspaces/demo"),
    ("PATCH", "/api/v1/workspaces/demo/deactivate"),
}


def packaged_routes() -> set[tuple[str, str]]:
    found: set[tuple[str, str]] = set()
    for route in app.routes:
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", set()) or set()
        if not path:
            continue
        if not methods:
            found.add(("MOUNT", str(path)))
        for method in methods:
            found.add((str(method).upper(), str(path)))
    return found


def main() -> None:
    found = packaged_routes()
    missing = sorted(REQUIRED_ROUTES - found)
    if missing:
        rendered = ", ".join(f"{method} {path}" for method, path in missing)
        all_routes = "; ".join(f"{method} {path}" for method, path in sorted(found))
        raise SystemExit(
            "Sprint 8B route verification failed. "
            f"backend_root={BACKEND_ROOT}; app_package={getattr(app_package, '__file__', None)}; "
            f"main_module={getattr(main_module, '__file__', None)}; missing={rendered}; "
            f"packaged_routes={all_routes or 'none'}"
        )
    rendered = ", ".join(f"{method} {path}" for method, path in sorted(REQUIRED_ROUTES))
    print(f"Sprint 8B routes verified: {rendered}")


if __name__ == "__main__":
    main()
