"""Global search guardrails: bounded, tenant-filtered and non-financial results."""
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy.dialects.postgresql import dialect

from app.api.v1.search import SearchResult, search_records
from app.dependencies.rbac import require_min_role
from app.models.customer import Customer
from app.models.lead import Lead
from app.models.order import Order
from app.models.product import Product
from app.models.role import RoleName
from app.models.shipment import Shipment
from app.services.global_search_service import PER_KIND_LIMIT, _pattern, global_search


class FakeResult:
    def __init__(self, rows):
        self.rows = rows

    def all(self):
        return self.rows


class AuditedDb:
    def __init__(self, workspace_id, *, matching=False):
        self.workspace_id = workspace_id
        self.compiled = []
        self.matching = matching

    def scalars(self, stmt):
        sql = str(stmt.compile(dialect=dialect(), compile_kwargs={"literal_binds": True}))
        self.compiled.append(sql)
        model = stmt.column_descriptions[0]["entity"]
        if not self.matching:
            return FakeResult([])
        item = {
            Order: SimpleNamespace(id=uuid4(), order_number="ORD-2026-1", status="NEW"),
            Customer: SimpleNamespace(id=uuid4(), name="Customer", phone="123", instagram_username="customer"),
            Lead: SimpleNamespace(id=uuid4(), name="Lead", phone="123", instagram_username="lead"),
            Product: SimpleNamespace(id=uuid4(), name="Watch", sku="SKU-1"),
            Shipment: SimpleNamespace(id=uuid4(), tracking_number="204500000001", recipient_name="Recipient"),
        }[model]
        return FakeResult([item])


def test_search_sql_is_scoped_and_bounded_per_type():
    workspace_id = uuid4()
    db = AuditedDb(workspace_id, matching=True)
    results = global_search(db, workspace_id, "2045")
    assert len(db.compiled) == 5
    assert len(results) == 5
    for sql in db.compiled:
        assert str(workspace_id) in sql
        assert "deleted_at IS NULL" in sql
        assert f"LIMIT {PER_KIND_LIMIT}" in sql
    assert results[0]["href"].startswith("/orders?order_id=")
    assert results[1]["href"].startswith("/customers?customer_id=")
    assert results[2]["href"].startswith("/leads?lead_id=")
    assert results[3]["href"].startswith("/products?product_id=")
    assert results[4]["href"].startswith("/shipments?shipment_id=")
    assert all(set(row) == {"kind", "id", "title", "subtitle", "href"} for row in results)
    assert "product_variants.workspace_id" in db.compiled[3]
    assert "product_variants.deleted_at IS NULL" in db.compiled[3]


def test_input_like_metacharacters_are_literal():
    assert _pattern("50%_\\") == r"%50\%\_\\%"
    db = AuditedDb(uuid4())
    assert global_search(db, db.workspace_id, " ") == []
    assert len(db.compiled) == 0
    assert global_search(db, db.workspace_id, "A%") == []


def test_endpoint_needs_membership_and_schema_cannot_surface_financial_fields():
    workspace = uuid4()
    guard = require_min_role(RoleName.ANALYST)
    with pytest.raises(HTTPException) as err:
        guard(user=SimpleNamespace(workspaces=[]), workspace_id=workspace)
    assert err.value.status_code == 403
    result = search_records(q="AB", workspace_id=workspace, db=AuditedDb(workspace))
    assert result == []
    fields = set(SearchResult.model_fields)
    assert fields == {"kind", "id", "title", "subtitle", "href"}
