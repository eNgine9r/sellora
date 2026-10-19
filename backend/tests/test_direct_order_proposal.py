"""Production repositories/service/route on disposable SQL tables; never live DB."""
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Column, JSON, MetaData, Table, create_engine, event
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.ai.services.ai_gateway_service import AIGatewayService
from app.api.v1.direct import router
from app.database.session import get_db
from app.dependencies.auth import get_current_user
from app.models.ai_direct import AIAnalysis, DirectConversation, DirectMessage
from app.models.inventory import Inventory
from app.models.product import Product
from app.models.product_variant import ProductVariant
from app.repositories.ai_direct_repository import AIRepository
from app.services.direct_order_proposal_service import DirectOrderProposalService, ProposalConversationNotFound

STAMP = datetime(2026, 10, 19, 10, tzinfo=UTC)


@pytest.fixture
def sql():
    engine = create_engine("sqlite+pysqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    metadata = MetaData()
    for model in (AIAnalysis, DirectConversation, DirectMessage, Inventory, Product, ProductVariant):
        Table(model.__tablename__, metadata, *[
            Column(c.name, JSON() if isinstance(c.type, JSONB) else c.type, primary_key=c.primary_key, nullable=c.nullable)
            for c in model.__table__.columns
        ])
    metadata.create_all(engine)
    with Session(engine, autoflush=False) as db:
        statements = []
        event.listen(engine, "before_cursor_execute", lambda _c, _u, text, _p, _x, _m: statements.append(text))
        yield db, statements
    engine.dispose()


def insert(db, entity_type, **values):
    fields = {"id": uuid4(), "created_at": STAMP, **values}
    if "updated_at" in entity_type.__table__.columns:
        fields.setdefault("updated_at", fields["created_at"])
    db.execute(entity_type.__table__.insert().values(**fields))
    return fields["id"]


def seed(db):
    workspace, other = uuid4(), uuid4()
    conversation = insert(db, DirectConversation, workspace_id=workspace)
    product = insert(db, Product, workspace_id=workspace, name="Светр", sku="ROOT", is_active=True)
    variant = insert(db, ProductVariant, workspace_id=workspace, product_id=product, sku="SKU-1", color="Чорний", size="M", price=Decimal("100"), is_active=True)
    insert(db, Inventory, workspace_id=workspace, product_variant_id=variant, stock_quantity=20, reserved_quantity=2)
    message = insert(db, DirectMessage, workspace_id=workspace, conversation_id=conversation, direction="INBOUND", sender_type="CUSTOMER", message_type="TEXT", text="Хочу SKU-1", received_at=STAMP)
    return SimpleNamespace(workspace=workspace, other=other, conversation=conversation, product=product, variant=variant, message=message)


def analysis(db, data, mentions, **overrides):
    return insert(db, AIAnalysis, workspace_id=data.workspace, conversation_id=data.conversation,
        source_message_id=data.message, provider="synthetic", model="synthetic", prompt_key="DIRECT_MESSAGE_ANALYSIS",
        prompt_version="v1", status="COMPLETED", created_at=STAMP + timedelta(minutes=1),
        structured_result={"intent": "ORDER_REQUEST", "intent_confidence": 0.8, "summary": "Products",
                           "recommended_action": "CREATE_ORDER_DRAFT", "suggested_reply": None,
                           "extracted_entities": {"product_mentions": mentions}}, **overrides)


def get(db, data):
    return DirectOrderProposalService(db).get(data.workspace, data.conversation)


@pytest.mark.parametrize("mention,status,reason", [
    ({"text": "anything", "sku": "  sku-1  ", "color": " чорний ", "size": "m"}, "MATCHED", "UNIQUE_EXACT_MATCH"),
    ({"text": "  СВЕТР "}, "MATCHED", "UNIQUE_EXACT_MATCH"),
    ({"text": " ROOT "}, "MATCHED", "UNIQUE_EXACT_MATCH"),
    ({"text": "Светр", "sku": "UNKNOWN"}, "NOT_FOUND", "UNKNOWN_SKU"),
    ({"text": "Светр", "sku": "SKU-1", "size": "L"}, "NOT_FOUND", "SKU_ATTRIBUTE_CONFLICT"),
    ({"text": "partial Светр extra"}, "NOT_FOUND", "NO_EXACT_MATCH"),
])
def test_exact_matching_uses_catalog_not_first_row(sql, mention, status, reason):
    db, _ = sql; data = seed(db); analysis(db, data, [mention])
    result = get(db, data)
    line = next(line for line in result.lines if line.source == "ANALYSIS_CONTEXT")
    assert line.match_status == status and line.reason == reason
    assert line.requires_review and line.evidence == []
    if status == "MATCHED":
        assert line.candidates[0].variant_id == data.variant
        assert line.candidates[0].available_quantity == 18
    assert result.analysis_state == "COMPLETED"  # No reply suggestion required.


def test_duplicate_names_variants_and_skus_remain_ambiguous(sql):
    db, _ = sql; d = seed(db)
    duplicate = insert(db, Product, workspace_id=d.workspace, name="Светр", is_active=True)
    second = insert(db, ProductVariant, workspace_id=d.workspace, product_id=duplicate, sku="sku-1", color="Білий", size="L", price=None, is_active=True)
    analysis(db, d, [{"text": "Светр"}, {"text": "SKU-1", "sku": "SKU-1"}])
    result = get(db, d)
    assert all(line.match_status == "AMBIGUOUS" for line in result.lines)
    candidate = next(c for c in result.lines[0].candidates if c.variant_id == second)
    assert candidate.price is None and candidate.available_quantity is None


@pytest.mark.parametrize("kind", ["foreign_product", "deleted_product", "inactive_product", "foreign_variant", "deleted_variant", "inactive_variant"])
def test_catalog_scope_and_visibility(sql, kind):
    db, _ = sql; d = seed(db)
    model = Product if kind.endswith("product") else ProductVariant
    identity = d.product if model is Product else d.variant
    values = {"workspace_id": d.other} if kind.startswith("foreign") else {"deleted_at": STAMP} if kind.startswith("deleted") else {"is_active": False}
    db.execute(model.__table__.update().where(model.id == identity).values(**values))
    analysis(db, d, [{"text": "Светр"}])
    result = get(db, d)
    assert not any(line.candidates for line in result.lines)


def test_foreign_or_deleted_inventory_is_unknown(sql):
    db, _ = sql; d = seed(db)
    db.execute(Inventory.__table__.update().values(workspace_id=d.other))
    analysis(db, d, [{"text": "Светр"}])
    assert get(db, d).lines[0].candidates[0].available_quantity is None
    db.execute(Inventory.__table__.update().values(workspace_id=d.workspace, deleted_at=STAMP))
    assert get(db, d).lines[0].candidates[0].available_quantity is None


@pytest.mark.parametrize("text,expected", [
    ("Хочу sku-1 SKU-1 SKU-1", True), ("SKU-10", False), ("XSKU-1", False),
    ("SKU-1-RED", False), ('"SKU-1"', False), ("SKU-1,", False), ("(SKU-1)", False),
])
def test_inbound_literal_token_boundaries_and_repetition(sql, text, expected):
    db, _ = sql; d = seed(db)
    db.execute(DirectMessage.__table__.update().values(text=text))
    result = get(db, d)
    assert result.analysis_state == "MISSING"
    assert len(result.lines) == int(expected)
    if expected:
        line = result.lines[0]
        assert line.source == "INBOUND_SKU" and line.quantity == 1 and not line.requires_review
        assert line.evidence[0].message_id == d.message and "sku-1" in line.evidence[0].snippet.lower()


def test_outbound_and_deleted_text_never_provide_evidence(sql):
    db, _ = sql; d = seed(db)
    db.execute(DirectMessage.__table__.update().values(direction="OUTBOUND"))
    assert get(db, d).lines == []
    db.execute(DirectMessage.__table__.update().values(direction="INBOUND", deleted_at=STAMP))
    assert get(db, d).lines == []


def test_newest_generic_attempt_not_contact_extraction_and_no_resurrection(sql):
    db, _ = sql; d = seed(db)
    first = analysis(db, d, [{"text": "Светр"}])
    insert(db, AIAnalysis, workspace_id=d.workspace, conversation_id=d.conversation, source_message_id=d.message,
           provider="synthetic", model="synthetic", prompt_key="DIRECT_CUSTOMER_DATA_EXTRACTION",
           prompt_version="v1", status="COMPLETED", structured_result={}, created_at=STAMP + timedelta(minutes=2))
    assert get(db, d).analysis_id == first
    insert(db, AIAnalysis, workspace_id=d.workspace, conversation_id=d.conversation, source_message_id=d.message,
           provider="synthetic", model="synthetic", prompt_key="DIRECT_MESSAGE_ANALYSIS",
           prompt_version="v1", status="FAILED_SAFE", structured_result={}, created_at=STAMP + timedelta(minutes=3))
    result = get(db, d)
    assert result.analysis_state == "FAILED"
    assert all(line.source == "INBOUND_SKU" for line in result.lines)


@pytest.mark.parametrize("change", ["import", "edit", "delete"])
def test_freshness_uses_storage_edit_times_not_provider_received_time(sql, change):
    db, _ = sql; d = seed(db); analysis(db, d, [{"text": "Светр"}])
    later = STAMP + timedelta(minutes=2)
    if change == "import":
        insert(db, DirectMessage, workspace_id=d.workspace, conversation_id=d.conversation, direction="INBOUND",
               sender_type="CUSTOMER", message_type="TEXT", text="other", received_at=STAMP - timedelta(days=10), created_at=later)
    else:
        db.execute(DirectMessage.__table__.update().values(**({"updated_at": later, "text": "edited"} if change == "edit" else {"deleted_at": later})))
    result = get(db, d)
    assert result.analysis_state == "STALE"
    assert all(line.requires_review for line in result.lines if line.source == "ANALYSIS_CONTEXT")


def test_malformed_empty_and_foreign_analysis(sql):
    db, _ = sql; d = seed(db)
    identity = analysis(db, d, [])
    assert get(db, d).analysis_state == "COMPLETED"
    db.execute(AIAnalysis.__table__.update().where(AIAnalysis.id == identity).values(structured_result={}))
    assert get(db, d).analysis_state == "MALFORMED"
    db.execute(AIAnalysis.__table__.update().values(workspace_id=d.other))
    assert get(db, d).analysis_state == "MISSING"
    with pytest.raises(ProposalConversationNotFound):
        DirectOrderProposalService(db).get(d.other, d.conversation)


def test_partial_catalog_never_proves_uniqueness(sql):
    db, _ = sql; d = seed(db); analysis(db, d, [{"text": "Светр", "sku": "SKU-1"}])
    for i in range(500):
        insert(db, ProductVariant, workspace_id=d.workspace, product_id=d.product, sku=f"EXTRA-{i}", color=str(i), is_active=True)
    result = get(db, d)
    assert result.catalog_truncated
    assert result.lines[0].reason == "CATALOG_LIMIT" and not result.lines[0].candidates


def test_api_analyst_read_is_provider_free_and_workspace_isolated(sql, monkeypatch):
    db, statements = sql; d = seed(db); analysis(db, d, [{"text": "Светр"}])
    monkeypatch.setattr(AIRepository, "get_or_create_settings", lambda *_: pytest.fail("GET initialized settings"))
    monkeypatch.setattr(AIGatewayService, "generate_structured_response", lambda *_: pytest.fail("GET called provider"))
    app = FastAPI(); app.include_router(router, prefix="/api/v1")
    user = SimpleNamespace(id=uuid4(), workspaces=[SimpleNamespace(workspace_id=d.workspace, is_active=True,
        workspace=SimpleNamespace(is_active=True), role=SimpleNamespace(name="ANALYST"))])
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: user
    client = TestClient(app); statements.clear()
    response = client.get(f"/api/v1/direct/conversations/{d.conversation}/order-proposal", headers={"X-Workspace-ID": str(d.workspace)})
    assert response.status_code == 200
    assert set(response.json()) == {"conversation_id", "analysis_id", "analysis_created_at", "analysis_context_message_id", "analysis_state", "catalog_truncated", "context_truncated", "lines"}
    assert all(statement.lstrip().upper().startswith("SELECT") for statement in statements)
    assert len(statements) <= 6  # Conversation, analysis, messages, catalog, inventory, freshness.
    assert client.get(f"/api/v1/direct/conversations/{d.conversation}/order-proposal", headers={"X-Workspace-ID": str(d.other)}).status_code == 403
    assert client.get(f"/api/v1/direct/conversations/{uuid4()}/order-proposal", headers={"X-Workspace-ID": str(d.workspace)}).status_code == 404


@pytest.mark.parametrize("payload", [
    {"intent": "ORDER_REQUEST", "intent_confidence": 0.8, "summary": "x", "recommended_action": "CREATE_ORDER_DRAFT"},
    {"intent": "ORDER_REQUEST", "intent_confidence": 0.8, "summary": "x", "recommended_action": "CREATE_ORDER_DRAFT", "extracted_entities": {}},
])
def test_missing_saved_mentions_is_malformed_not_valid_empty(sql, payload):
    db, _ = sql; d = seed(db); identity = analysis(db, d, [])
    db.execute(AIAnalysis.__table__.update().where(AIAnalysis.id == identity).values(structured_result=payload))
    assert get(db, d).analysis_state == "MALFORMED"


def test_explicit_parent_sku_narrows_attributes_but_variant_sku_has_priority(sql):
    db, _ = sql; d = seed(db)
    second = insert(db, ProductVariant, workspace_id=d.workspace, product_id=d.product, sku="SKU-2", color="Білий", size="L", price=None, is_active=True)
    identity = analysis(db, d, [
        {"text": "ignored", "sku": " root ", "color": " білий ", "size": "l"},
        {"text": "ignored", "sku": "ROOT"},
        {"text": "ignored", "sku": "ROOT", "size": "XXL"},
        {"text": "ignored", "sku": "SKU-1", "size": "   ", "color": "  "},
    ])
    lines = [line for line in get(db, d).lines if line.source == "ANALYSIS_CONTEXT"]
    assert lines[0].match_status == "MATCHED" and lines[0].matched_by == "PRODUCT_SKU"
    assert lines[0].candidates[0].variant_id == second
    assert lines[1].match_status == "AMBIGUOUS"
    assert lines[2].match_status == "NOT_FOUND"
    assert lines[3].match_status == "MATCHED" and lines[3].matched_by == "VARIANT_SKU"


def test_context_bounds_and_deduplication_never_inflate_quantity(sql):
    db, _ = sql; d = seed(db)
    analysis(db, d, [{"text": "Светр", "quantity": 2}, {"text": "Светр", "quantity": 3}])
    result = get(db, d)
    ai = [line for line in result.lines if line.source == "ANALYSIS_CONTEXT"]
    assert len(ai) == 1 and ai[0].quantity == 2
    for i in range(51):
        insert(db, DirectMessage, workspace_id=d.workspace, conversation_id=d.conversation, direction="INBOUND", sender_type="CUSTOMER",
               message_type="TEXT", text="x" * 4100, received_at=STAMP, created_at=STAMP + timedelta(minutes=i + 2))
    result = get(db, d)
    assert result.context_truncated and result.analysis_state == "STALE"
    assert all(line.source == "ANALYSIS_CONTEXT" for line in result.lines)


def test_analysis_anchor_is_context_only_and_never_foreign(sql):
    db, _ = sql; d = seed(db); identity = analysis(db, d, [{"text": "Светр"}])
    db.execute(AIAnalysis.__table__.update().where(AIAnalysis.id == identity).values(source_message_id=uuid4()))
    result = get(db, d)
    assert result.analysis_context_message_id is None
    assert all(line.evidence == [] for line in result.lines if line.source == "ANALYSIS_CONTEXT")


def test_candidate_display_cap_never_turns_ambiguity_into_unique(sql):
    db, _ = sql; d = seed(db)
    for i in range(11):
        insert(db, ProductVariant, workspace_id=d.workspace, product_id=d.product, sku=f"OTHER-{i}", color=str(i), size="L", is_active=True)
    analysis(db, d, [{"text": "Светр"}])
    line = get(db, d).lines[0]
    assert line.match_status == "AMBIGUOUS"
    assert line.candidates_truncated and len(line.candidates) == 10


@pytest.mark.parametrize("boundary", ["per_message", "total_context"])
def test_clipping_cannot_manufacture_an_exact_sku_token(sql, boundary):
    db, _ = sql; d = seed(db)
    text = ("x" * 3994 + " " if boundary == "per_message" else "") + "SKU-1-RED"
    db.execute(DirectMessage.__table__.update().where(DirectMessage.id == d.message).values(text=text))
    if boundary == "total_context":
        for i in range(5):
            insert(db, DirectMessage, workspace_id=d.workspace, conversation_id=d.conversation, direction="INBOUND",
                   sender_type="CUSTOMER", message_type="TEXT", text="x" * 3999,
                   received_at=STAMP, created_at=STAMP + timedelta(minutes=i + 1))
    result = get(db, d)
    assert result.context_truncated and result.lines == []
