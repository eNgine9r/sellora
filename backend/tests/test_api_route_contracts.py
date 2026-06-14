from app.main import app
from app.schemas.lead import LeadCreate
from app.schemas.product import ProductCreate, ProductVariantCreate


def _iter_routes(routes, prefix: str = ""):
    for route in routes:
        include_context = getattr(route, "include_context", None)
        original_router = getattr(route, "original_router", None)
        if include_context is not None and original_router is not None:
            yield from _iter_routes(original_router.routes, f"{prefix}{include_context.prefix}")
            continue
        route_path = getattr(route, "path", None)
        if route_path is not None:
            yield route, f"{prefix}{route_path}"


def _route_index(path: str, method: str = "GET") -> int:
    for index, (route, route_path) in enumerate(_iter_routes(app.routes)):
        if route_path == path and method in getattr(route, "methods", set()):
            return index
    raise AssertionError(f"Route {method} {path} is not registered")


def test_static_product_variant_routes_are_registered_before_product_id_route() -> None:
    assert _route_index("/api/v1/products/variants", "GET") < _route_index("/api/v1/products/{product_id}", "GET")
    assert _route_index("/api/v1/products/variants", "POST") < _route_index("/api/v1/products/{product_id}", "GET")


def test_feedback_routes_are_registered() -> None:
    assert _route_index("/api/v1/feedback", "POST") >= 0
    assert _route_index("/api/v1/feedback", "GET") >= 0
    assert _route_index("/api/v1/feedback/{feedback_id}", "PATCH") >= 0


def test_static_order_and_shipment_routes_are_registered_before_uuid_routes() -> None:
    assert _route_index("/api/v1/orders/dashboard", "GET") < _route_index("/api/v1/orders/{order_id}", "GET")
    assert _route_index("/api/v1/shipments/summary", "GET") < _route_index("/api/v1/shipments/{shipment_id}", "GET")


def test_create_schemas_accept_minimal_staging_payloads() -> None:
    lead = LeadCreate.model_validate({"name": "Synthetic Lead"})
    product = ProductCreate.model_validate({"name": "Synthetic Product"})

    assert lead.name == "Synthetic Lead"
    assert lead.lead_source_id is None
    assert product.name == "Synthetic Product"
    assert product.images == []


def test_product_variant_schema_uses_actual_backend_field_names() -> None:
    import uuid

    product_id = uuid.uuid4()
    payload = ProductVariantCreate.model_validate({"product_id": product_id, "sku": "SYN-VAR-1", "price": 10})

    assert payload.product_id == product_id
    assert payload.sku == "SYN-VAR-1"
