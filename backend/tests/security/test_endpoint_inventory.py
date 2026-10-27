from collections import Counter

from fastapi.routing import APIRoute

from app.main import app


PUBLIC_ENDPOINTS = {"/health", "/health/live", "/health/ready", "/api/v1/auth/login", "/api/v1/auth/refresh",
    "/api/v1/auth/session/login", "/api/v1/auth/session/refresh", "/api/v1/auth/session/logout"}
PUBLIC_METHOD_ENDPOINTS = {("GET", "/api/v1/integrations/meta-ads/oauth/callback")}
AUTHENTICATED_GLOBAL_ENDPOINTS = {"/api/v1/auth/me", "/api/v1/workspaces", "/api/v1/workspaces/demo",
    "/api/v1/auth/session/upgrade", "/api/v1/auth/session/logout-all"}
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
    "/api/v1/workspace-memos",
)
OWNER_ONLY_ENDPOINTS = {
    ("POST", "/api/v1/integrations/meta-ads/oauth/start"),
    ("POST", "/api/v1/integrations/meta-ads/oauth/callback"),
    ("POST", "/api/v1/integrations/meta-ads/disconnect"),
    ("GET", "/api/v1/integrations/meta-ads/accounts"),
    ("POST", "/api/v1/integrations/meta-ads/account"),
    ("POST", "/api/v1/integrations/meta-ads/sync"),
    ("POST", "/api/v1/workspace-users"),
    ("PUT", "/api/v1/workspace-users/{user_id}/role"),
    ("PATCH", "/api/v1/workspace-users/{user_id}/deactivate"),
    ("PUT", "/api/v1/workspaces/current"),
    ("PUT", "/api/v1/orders/{order_id}/product-costs"),
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
    "PUBLIC": 9,
    "AUTHENTICATED_GLOBAL": 6,
    "WORKSPACE_SCOPED": 218,
    "FEATURE_GATED": 15,
    "INTERNAL_OR_DOCUMENTATION": 0,
}
EXPECTED_TOTAL_ROUTES = 248
EXPECTED_MUTATION_ROUTES = 141

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
EXPECTED_HISTORY_CANCEL_ROUTES = {("POST", "/api/v1/direct/history-sync/cancel")}
EXPECTED_DIRECT_ORDER_EVIDENCE_ROUTES = {
    ("GET", "/api/v1/direct/conversations/{conversation_id}/order-evidence"),
    ("POST", "/api/v1/direct/conversations/{conversation_id}/order-evidence/confirm"),
}

EXPECTED_DIRECT_CUSTOMER_EXTRACTION_ROUTES = {
    ("GET", "/api/v1/direct/conversations/{conversation_id}/customer-data-extraction"),
    ("POST", "/api/v1/direct/conversations/{conversation_id}/customer-data-extraction/extract"),
    ("POST", "/api/v1/direct/conversations/{conversation_id}/customer-data-extraction/apply"),
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


def _primary_scope(path: str, method: str | None = None) -> str:
    if path in PUBLIC_ENDPOINTS or (method, path) in PUBLIC_METHOD_ENDPOINTS:
        return "PUBLIC"
    if path in AUTHENTICATED_GLOBAL_ENDPOINTS:
        return "AUTHENTICATED_GLOBAL"
    if path.startswith(FEATURE_GATED_PREFIXES):
        return "FEATURE_GATED"
    if path.startswith(WORKSPACE_PREFIXES):
        return "WORKSPACE_SCOPED"
    return "INTERNAL_OR_DOCUMENTATION"


def test_history_cancel_endpoint_is_explicitly_workspace_scoped() -> None:
    routes = { (method, path): route for path, route in _api_routes() for method in route.methods }
    assert EXPECTED_HISTORY_CANCEL_ROUTES.issubset(routes)
    assert all(_primary_scope(path) == "WORKSPACE_SCOPED" for _method, path in EXPECTED_HISTORY_CANCEL_ROUTES)


def test_endpoint_inventory_primary_classifications_are_exactly_reconciled() -> None:
    routes = _api_routes()
    primary_counts = Counter(_primary_scope(path, next(iter(route.methods))) for path, route in routes)
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


def test_customer_order_history_is_workspace_scoped_and_not_public() -> None:
    path = "/api/v1/customers/{customer_id}/orders"
    routes = _api_routes()
    matches = [(route_path, route) for route_path, route in routes if route_path == path]
    assert len(matches) == 1
    assert matches[0][1].methods == {"GET"}
    assert _primary_scope(path) == "WORKSPACE_SCOPED"
    assert path not in PUBLIC_ENDPOINTS and path not in AUTHENTICATED_GLOBAL_ENDPOINTS


def test_global_endpoint_whitelist_is_explicit_and_small() -> None:
    global_paths = {path for path, route in _api_routes() if _primary_scope(path, next(iter(route.methods))) in {"PUBLIC", "AUTHENTICATED_GLOBAL"}}

    assert PUBLIC_ENDPOINTS.issubset(global_paths)
    assert AUTHENTICATED_GLOBAL_ENDPOINTS.issubset(global_paths)
    assert "/api/v1/workspaces/current" not in global_paths
    assert global_paths == PUBLIC_ENDPOINTS | AUTHENTICATED_GLOBAL_ENDPOINTS | {path for _, path in PUBLIC_METHOD_ENDPOINTS}


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


def test_direct_customer_extraction_routes_are_explicit_and_workspace_scoped() -> None:
    routes = _api_routes()
    actual_routes = {
        (method, path)
        for path, route in routes
        for method in route.methods
    }

    assert EXPECTED_DIRECT_CUSTOMER_EXTRACTION_ROUTES.issubset(actual_routes)
    assert all(
        _primary_scope(path) == "WORKSPACE_SCOPED"
        for _method, path in EXPECTED_DIRECT_CUSTOMER_EXTRACTION_ROUTES
    )


def test_meta_oauth_redirect_is_public_but_code_exchange_is_owner_scoped():
    path = "/api/v1/integrations/meta-ads/oauth/callback"
    assert _primary_scope(path, "GET") == "PUBLIC"
    assert _primary_scope(path, "POST") == "FEATURE_GATED"
    assert ("POST", path) in OWNER_ONLY_ENDPOINTS


def test_crm_attribution_report_is_read_only_and_workspace_scoped() -> None:
    path = "/api/v1/advertising/crm-attribution"
    matching = [route for route_path, route in _api_routes() if route_path == path]
    assert len(matching) == 1
    assert matching[0].methods == {"GET"}
    assert _primary_scope(path) == "WORKSPACE_SCOPED"
    assert path not in PUBLIC_ENDPOINTS and path not in AUTHENTICATED_GLOBAL_ENDPOINTS



def test_direct_order_evidence_routes_are_explicitly_tenant_scoped() -> None:
    routes = _api_routes()
    matches = {
        (method, path): route
        for path, route in routes
        for method in route.methods
        if (method, path) in EXPECTED_DIRECT_ORDER_EVIDENCE_ROUTES
    }
    assert set(matches) == EXPECTED_DIRECT_ORDER_EVIDENCE_ROUTES
    for (_method, path), route in matches.items():
        assert _primary_scope(path) == "WORKSPACE_SCOPED"
        assert path not in PUBLIC_ENDPOINTS
        assert path not in AUTHENTICATED_GLOBAL_ENDPOINTS

    # This is deliberately an ANALYST+ read and MANAGER+ write flow.
    read_path = "/api/v1/direct/conversations/{conversation_id}/order-evidence"
    confirm_path = read_path + "/confirm"
    assert matches[("GET", read_path)].name == "get_direct_order_evidence"
    assert matches[("POST", confirm_path)].name == "confirm_direct_order_evidence"
