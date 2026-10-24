"""Prove deterministic attribution never guesses, crosses tenants or overwrites CRM."""
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.services.advertising_attribution_service import AdvertisingAttributionService


class FakeRows:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value

    def one(self):
        return self.value

    def all(self):
        return self.value


class FakeDb:
    def __init__(self, *, lead=None, campaign=None, stats=None, grouped=None):
        self.responses = [lead, campaign]
        self.query_count = 0
        self.stat_responses = [stats or (0, 0, Decimal("0"), 0), grouped or []]
        self.flushes = 0
        self.commits = 0
        self.statements = []

    def execute(self, statement):
        self.statements.append(statement)
        if self.query_count < 2:
            result = FakeRows(self.responses[self.query_count])
        else:
            result = FakeRows(self.stat_responses[self.query_count - 2])
        self.query_count += 1
        return result

    def flush(self):
        self.flushes += 1

    def commit(self):
        self.commits += 1


class FakeOrders:
    def __init__(self, order):
        self.order = order
        self.calls = []

    def get_for_update(self, workspace_id, order_id):
        self.calls.append((workspace_id, order_id))
        return self.order if self.order and self.order.workspace_id == workspace_id and self.order.id == order_id else None


class FakeAudit:
    def __init__(self):
        self.records = []

    def create(self, **data):
        self.records.append(data)


def make_service(*, explicit_lead=True, existing_campaign=None, wrong_customer=False, cross_workspace=False, deleted_lead=False):
    ws = uuid4()
    customer_id = uuid4()
    campaign_id = uuid4()
    lead_id = uuid4()
    order = SimpleNamespace(
        id=uuid4(), workspace_id=ws, customer_id=uuid4() if wrong_customer else customer_id,
        campaign_id=existing_campaign,
    )
    conversation = SimpleNamespace(
        id=uuid4(),
        workspace_id=uuid4() if cross_workspace else ws,
        linked_lead_id=lead_id if explicit_lead else None,
    )
    lead = None if deleted_lead else SimpleNamespace(id=lead_id, campaign_id=campaign_id)
    db = FakeDb(lead=lead, campaign=campaign_id)
    service = AdvertisingAttributionService.__new__(AdvertisingAttributionService)
    service.db = db
    service.orders = FakeOrders(order)
    service.audit = FakeAudit()
    return service, ws, customer_id, conversation, order, campaign_id


def test_verified_direct_lead_inherits_campaign_once_and_audits():
    service, ws, customer_id, conversation, order, campaign_id = make_service()
    assert service.inherit_verified_direct_lead(ws, conversation, customer_id, order.id, None)
    assert order.campaign_id == campaign_id
    assert service.db.flushes == 1
    assert service.db.commits == 0
    assert service.audit.records[0]["action"] == "DIRECT_LEAD_CAMPAIGN_INHERITED"
    assert service.audit.records[0]["new_value"]["lead_id"] == str(conversation.linked_lead_id)
    assert not service.inherit_verified_direct_lead(ws, conversation, customer_id, order.id, None)
    assert len(service.audit.records) == 1


@pytest.mark.parametrize("scenario", ["no_lead", "manual", "wrong_customer", "cross_workspace", "missing_lead"])
def test_no_guess_no_overwrite_or_cross_tenant(scenario):
    manual = uuid4()
    service, ws, customer_id, conversation, order, _ = make_service(
        explicit_lead=scenario != "no_lead",
        existing_campaign=manual if scenario == "manual" else None,
        wrong_customer=scenario == "wrong_customer",
        cross_workspace=scenario == "cross_workspace",
        deleted_lead=scenario == "missing_lead",
    )
    assert not service.inherit_verified_direct_lead(ws, conversation, customer_id, order.id, None)
    assert order.campaign_id == (manual if scenario == "manual" else None)
    assert not service.audit.records
    assert service.db.flushes == 0
    assert service.db.commits == 0


def test_campaign_missing_or_soft_deleted_remains_unattributed():
    service, ws, customer_id, conversation, order, _ = make_service()
    service.db.responses[1] = None
    assert not service.inherit_verified_direct_lead(ws, conversation, customer_id, order.id, None)
    assert order.campaign_id is None
    assert len(service.db.statements) == 2
    compiled = [str(stmt) for stmt in service.db.statements]
    assert all("workspace_id" in query and "deleted_at" in query for query in compiled)


def test_crm_report_not_derived_from_meta_daily_metrics():
    ws = uuid4()
    campaign = uuid4()
    db = FakeDb(stats=(3, 2, Decimal("799.00"), 4), grouped=[(campaign, "Meta Campaign", 3, 2, Decimal("799.00"))])
    # Summary calls execute twice; it does not look at AdMetric or mutate data.
    db.query_count = 2
    service = AdvertisingAttributionService.__new__(AdvertisingAttributionService)
    service.db = db
    response = service.summary(ws, __import__("datetime").date(2026, 10, 1), __import__("datetime").date(2026, 10, 24))
    assert response["source"] == "crm_orders"
    assert response["completed_paid_orders"] == 2
    assert response["unattributed_completed_paid_orders"] == 4
    assert response["completed_paid_revenue"] == Decimal("799.00")
    assert response["campaigns"][0]["campaign_id"] == campaign
    assert all("ad_metrics" not in str(stmt) for stmt in db.statements)
    assert all("orders" in str(stmt) for stmt in db.statements)
    assert db.commits == 0


def test_invalid_range_rejected_before_query():
    service = AdvertisingAttributionService(FakeDb())
    from datetime import date
    with pytest.raises(ValueError, match="INVALID_DATE_RANGE"):
        service.summary(uuid4(), date(2026, 10, 25), date(2026, 10, 24))
