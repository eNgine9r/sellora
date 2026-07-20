from collections import Counter

from fastapi.routing import APIRoute

from app.main import app


PUBLIC_ENDPOINTS = {"/health", "/api/v1/auth/login", "/api/v1/auth/refresh"}
AUTHENTICATED_GLOBAL_ENDPOINTS = {"/api/v1/auth/me", "/api/v1/workspaces", "/api/v1/workspaces/demo"}
FEATURE_GATED_PREFIXES = ("/api/v1/integrations/meta-ads",)
WORKSPACE_PREFIXES = (
    "/api/v1/leads",
    "/api/v1/customers",
    "/api/v1/orders",
    "/api/v1/order-fulfillments",
    "/api/v1/products",
    "/api/v1/inventory",
    "/api/v1/shipments",
    "/api/v1/finance",
    "/api/v1/advertising",
    "/api/v1/analytics",
    "/api/v1/tags",
    "/api/v1/attachments",
    "/api/v1/import",
    "/api/v1/feedback",
    "/api/v1/lead-sources",
    "/api/v1/integrations/nova-poshta",
    "/api/v1/integrations/instagram",
    "/api/v1/workspace-users",
    "/api/v1/workspaces/current",
    "/api/v1/workspaces/demo/deactivate",
    "/api/v1/onboarding",
    "/api/v1/ai",
    "/api/v1/direct",
)
OWNER_ONLY_ENDPOINTS = {
    ("POST", "/api/v1/workspace-users"),
    ("PUT", "/api/v1/workspace-users/{user_id}/role"),
    ("PATCH", "/api/v1/workspace-users/{user_id}/deactivate"),
    ("PUT", "/api/v1/workspaces/current"),
    ("PATCH", "/api/v1/workspaces/demo/deactivate"),
    ("POST", "/api/v1/advertising/campaigns"),
    ("POST", "/api/v1/advertising/metrics"),
    ("PATCH", "/api/v1/ai/settings"),
    ("POST", "/api/v1/integrations/instagram/connect"),
    ("POST", "/api/v1/integrations/instagram/validate"),
    ("POST", "/api/v1/integrations/instagram/disconnect"),
    ("DELETE", "/api/v1/integrations/instagram/data"),
    ("POST", "/api/v1/integrations/instagram/webhooks/subscribe"),
    ("GET", "/api/v1/integrations/instagram/webhooks/status"),
    ("POST", "/api/v1/integrations/instagram/webhooks/unsubscribe"),
}
EXPECTED_PRIMARY_COUNTS = {
    "PUBLIC": 3,
    "AUTHENTICATED_GLOBAL": 4,
    "WORKSPACE_SCOPED": 192,
    "FEATURE_GATED": 12,
    "INTERNAL_OR_DOCUMENTATION": 0,
}
EXPECTED_TOTAL_ROUTES = 211
EXPECTED_MUTATION_ROUTES = 119

EXPECTED_CANONICAL_FULFILLMENT_ROUTES = {
    ("POST", "/api/v1/order-fulfillments"),
    ("POST", "/api/v1/orders/{order_id}/fulfillment/prepare"),
    ("POST", "/api/v1/orders/{order_id}/fulfillment/execute"),
    ("GET", "/api/v1/orders/{order_id}/fulfillment"),
    ("POST", "/api/v1/orders/{order_id}/fulfillment/reconcile"),
    ("POST", "/api/v1/orders/{order_id}/fulfillment/cancel"),
}
EXPECTED_DIRECT_CUSTOMER_AUTOMATION_ROUTES = {
    ("GET", "/api/v1/direct/conversations/{conversation_id}/customer-automation"),
    ("POST", "/api/v1/direct/conversations/{conversation_id}/customer-automation/ensure"),
    ("POST", "/api/v1/direct/conversations/{conversation_id}/customer-automation/complete"),
    ("POST", "/api/v1/direct/conversations/{conversation_id}/customer-automation/finalize-order"),
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


def _primary_scope(path: str) -> str:
    if path in PUBLIC_ENDPOINTS:
        return "PUBLIC"
    if path in AUTHENTICATED_GLOBAL_ENDPOINTS:
        return "AUTHENTICATED_GLOBAL"
    if path.startswith(FEATURE_GATED_PREFIXES):
        return "FEATURE_GATED"
    if path.startswith(WORKSPACE_PREFIXES):
        return "WORKSPACE_SCOPED"
    return "INTERNAL_OR_DOCUMENTATION"


def test_endpoint_inventory_primary_classifications_are_exactly_reconciled() -> None:
    routes = _api_routes()
    primary_counts = Counter(_primary_scope(path) for path, _route in routes)
    classified_total = sum(primary_counts.values())

    assert len(routes) == EXPECTED_TOTAL_ROUTES
    assert classified_total == EXPECTED_TOTAL_ROUTES
    assert {key: primary_counts[key] for key in EXPECTED_PRIMARY_COUNTS} == EXPECTED_PRIMARY_COUNTS


def test_endpoint_inventory_permission_subsets_are_not_counted_as_primary_scopes() -> None:
    routes = _api_routes()
    owner_only = [(method, path) for path, route in routes for method in route.methods if (method, path) in OWNER_ONLY_ENDPOINTS]
    mutation_routes = [(method, path) for path, route in routes for method in route.methods if method in {"POST", "PUT", "PATCH", "DELETE"}]

    assert len(owner_only) == len(OWNER_ONLY_ENDPOINTS)
    assert len(mutation_routes) == EXPECTED_MUTATION_ROUTES
    assert all(_primary_scope(path) in {"WORKSPACE_SCOPED", "FEATURE_GATED"} for _method, path in owner_only)


def test_global_endpoint_whitelist_is_explicit_and_small() -> None:
    global_paths = {path for path, _route in _api_routes() if _primary_scope(path) in {"PUBLIC", "AUTHENTICATED_GLOBAL"}}

    assert PUBLIC_ENDPOINTS.issubset(global_paths)
    assert AUTHENTICATED_GLOBAL_ENDPOINTS.issubset(global_paths)
    assert "/api/v1/workspaces/current" not in global_paths
    assert len(global_paths) == len(PUBLIC_ENDPOINTS | AUTHENTICATED_GLOBAL_ENDPOINTS)


def test_canonical_fulfillment_routes_are_explicit_and_workspace_scoped() -> None:
    routes = _api_routes()
    actual_routes = {
        (method, path)
        for path, route in routes
        for method in route.methods
    }

    assert EXPECTED_CANONICAL_FULFILLMENT_ROUTES.issubset(actual_routes)
    assert all(
        _primary_scope(path) == "WORKSPACE_SCOPED"
        for _method, path in EXPECTED_CANONICAL_FULFILLMENT_ROUTES
    )


def test_direct_customer_automation_routes_are_explicit_and_workspace_scoped() -> None:
    routes = _api_routes()
    actual_routes = {
        (method, path)
        for path, route in routes
        for method in route.methods
    }

    assert EXPECTED_DIRECT_CUSTOMER_AUTOMATION_ROUTES.issubset(actual_routes)
    assert all(
        _primary_scope(path) == "WORKSPACE_SCOPED"
        for _method, path in EXPECTED_DIRECT_CUSTOMER_AUTOMATION_ROUTES
    )
