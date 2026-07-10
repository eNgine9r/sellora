from fastapi.routing import APIRoute

from app.core.config import get_settings
from app.main import app


PUBLIC_ENDPOINTS = {"/health", "/api/v1/auth/login", "/api/v1/auth/refresh"}
WORKSPACE_PREFIXES = (
    "/api/v1/leads",
    "/api/v1/customers",
    "/api/v1/orders",
    "/api/v1/products",
    "/api/v1/inventory",
    "/api/v1/shipments",
    "/api/v1/finance",
    "/api/v1/advertising",
    "/api/v1/analytics",
    "/api/v1/tags",
    "/api/v1/attachments",
    "/api/v1/imports",
    "/api/v1/import",
    "/api/v1/feedback",
    "/api/v1/lead-sources",
    "/api/v1/meta-ads",
    "/api/v1/nova-poshta",
    "/api/v1/integrations",
    "/api/v1/workspace-users",
    "/api/v1/workspaces/current",
)
OWNER_ONLY_ENDPOINTS = {
    ("POST", "/api/v1/workspace-users"),
    ("PUT", "/api/v1/workspace-users/{user_id}/role"),
    ("PATCH", "/api/v1/workspace-users/{user_id}/deactivate"),
    ("PUT", "/api/v1/workspaces/current"),
    ("POST", "/api/v1/advertising/campaigns"),
    ("POST", "/api/v1/advertising/metrics"),
}


def _flatten_routes(routes, prefix: str = "") -> list[tuple[str, APIRoute]]:
    flattened: list[tuple[str, APIRoute]] = []
    for route in routes:
        if isinstance(route, APIRoute):
            flattened.append((f"{prefix}{route.path}", route))
        elif hasattr(route, "original_router") and hasattr(route, "include_context"):
            flattened.extend(_flatten_routes(route.original_router.routes, f"{prefix}{route.include_context.prefix}"))
        elif hasattr(route, "routes"):
            flattened.extend(_flatten_routes(route.routes, prefix))
    return flattened


def _api_routes() -> list[tuple[str, APIRoute]]:
    return _flatten_routes(app.routes)


def test_endpoint_inventory_has_expected_workspace_scoped_security_surface() -> None:
    routes = _api_routes()
    workspace_routes = [(path, route) for path, route in routes if path.startswith(WORKSPACE_PREFIXES)]
    owner_only = [(method, path) for path, route in routes for method in route.methods if (method, path) in OWNER_ONLY_ENDPOINTS]

    assert len(routes) >= 80
    assert len(workspace_routes) >= 65
    assert len(owner_only) == len(OWNER_ONLY_ENDPOINTS)


def test_global_endpoint_whitelist_is_explicit_and_small() -> None:
    public_or_global = {path for path, _route in _api_routes() if not path.startswith(WORKSPACE_PREFIXES)}

    assert PUBLIC_ENDPOINTS.issubset(public_or_global)
    assert "/api/v1/workspaces" in public_or_global
    assert "/api/v1/workspaces/current" not in public_or_global
    assert len(public_or_global - PUBLIC_ENDPOINTS - {"/api/v1/auth/me", "/api/v1/auth/logout", "/api/v1/workspaces", "/api/v1/workspaces/current"}) <= 8
