from collections import Counter
from inspect import getclosurevars

from fastapi.routing import APIRoute

from app.main import app
from app.dependencies.auth import get_current_user
from app.dependencies.rbac import get_workspace_id
from app.models.role import RoleName


PUBLIC_ENDPOINTS = {"/health/live", "/health/ready", "/health", "/api/v1/auth/login", "/api/v1/auth/refresh"}
COOKIE_SESSION_ENDPOINTS = {"/api/v1/auth/session/login", "/api/v1/auth/session/refresh", "/api/v1/auth/session/logout"}
AUTHENTICATED_GLOBAL_ENDPOINTS = {"/api/v1/auth/session/upgrade", "/api/v1/auth/session/logout-all", "/api/v1/auth/me", "/api/v1/workspaces", "/api/v1/workspaces/demo"}
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
    "PUBLIC": 5,
    "COOKIE_SESSION": 3,
    "AUTHENTICATED_GLOBAL": 6,
    "WORKSPACE_SCOPED": 199,
    "FEATURE_GATED": 12,
    "INTERNAL_OR_DOCUMENTATION": 0,
}
# Added GET /advertising/crm-attribution and Direct order-proposal: scoped reads, no mutations.
EXPECTED_TOTAL_ROUTES = 225
EXPECTED_MUTATION_ROUTES = 128

EXPECTED_CANONICAL_FULFILLMENT_ROUTES = {
    ("POST", "/api/v1/order-fulfillments"),
    ("POST", "/api/v1/orders/{order_id}/fulfillment/prepare"),
    ("POST", "/api/v1/orders/{order_id}/fulfillment/execute"),
    ("GET", "/api/v1/orders/{order_id}/fulfillment"),
    ("POST", "/api/v1/orders/{order_id}/fulfillment/reconcile"),
    ("POST", "/api/v1/orders/{order_id}/fulfillment/cancel"),
}
EXPECTED_DIRECT_LEAD_ROUTES = {
    ("POST", "/api/v1/direct/conversations/{conversation_id}/lead/ensure"),
}
EXPECTED_DIRECT_CUSTOMER_AUTOMATION_ROUTES = {
    ("GET", "/api/v1/direct/conversations/{conversation_id}/customer-automation"),
    ("POST", "/api/v1/direct/conversations/{conversation_id}/customer-automation/ensure"),
    ("POST", "/api/v1/direct/conversations/{conversation_id}/customer-automation/complete"),
    ("POST", "/api/v1/direct/conversations/{conversation_id}/customer-automation/finalize-order"),
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


def _primary_scope(path: str) -> str:
    if path in COOKIE_SESSION_ENDPOINTS:
        return "COOKIE_SESSION"
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


def test_direct_lead_mutation_is_workspace_scoped_and_manager_guarded() -> None:
    route = next(
        route for path, route in _api_routes()
        if path == "/api/v1/direct/conversations/{conversation_id}/lead/ensure"
    )
    assert route.methods == {"POST"}
    assert _primary_scope("/api/v1/direct/conversations/{conversation_id}/lead/ensure") == "WORKSPACE_SCOPED"
    # require_min_role(MANAGER) and get_workspace_id must remain in
    # route dependency graph; no anonymous or cross-tenant mutation.
    dependencies = {dep.call for dep in route.dependant.dependencies}
    assert get_workspace_id in dependencies
    assert any(
        getattr(dep.call, "__name__", "") == "guard"
        and RoleName.MANAGER in getclosurevars(dep.call).nonlocals.values()
        for dep in route.dependant.dependencies
    )


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


def test_crm_attribution_is_explicit_authenticated_workspace_read() -> None:
    path = "/api/v1/advertising/crm-attribution"
    matches = [route for route_path, route in _api_routes() if route_path == path]
    assert len(matches) == 1
    route = matches[0]
    assert route.methods == {"GET"}
    assert _primary_scope(path) == "WORKSPACE_SCOPED"
    pending = [route.dependant]
    calls = set()
    while pending:
        dependency = pending.pop()
        if dependency.call is not None:
            calls.add(dependency.call)
        pending.extend(dependency.dependencies)
    assert get_workspace_id in calls
    assert get_current_user in calls
    # Preserve the advertising read minimum, rather than merely adding a count.
    assert any(
        getattr(call, "__module__", "") == "app.dependencies.rbac"
        and getclosurevars(call).nonlocals.get("minimum_role") == RoleName.ANALYST
        for call in calls
    )


def test_direct_order_proposal_is_an_explicit_analyst_workspace_read() -> None:
    path = "/api/v1/direct/conversations/{conversation_id}/order-proposal"
    matches = [route for route_path, route in _api_routes() if route_path == path]
    assert len(matches) == 1
    route = matches[0]
    assert route.methods == {"GET"}
    assert _primary_scope(path) == "WORKSPACE_SCOPED"
    pending, calls = [route.dependant], set()
    while pending:
        dependency = pending.pop()
        if dependency.call is not None:
            calls.add(dependency.call)
        pending.extend(dependency.dependencies)
    assert get_workspace_id in calls and get_current_user in calls
    assert any(
        getattr(call, "__module__", "") == "app.dependencies.rbac"
        and getclosurevars(call).nonlocals.get("minimum_role") == RoleName.ANALYST
        for call in calls
    )
