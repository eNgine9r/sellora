from app.main import app


def test_order_based_fulfillment_routes_are_registered_on_canonical_router() -> None:
    paths = set(app.openapi()["paths"].keys())
    assert "/api/v1/order-fulfillments" in paths
    assert "/api/v1/orders/{order_id}/fulfillment/prepare" in paths
    assert "/api/v1/orders/{order_id}/fulfillment/execute" in paths
    assert "/api/v1/orders/{order_id}/fulfillment" in paths
