from types import SimpleNamespace

import pytest

from app.repositories.customer_repository import InstagramIdentityConflict, select_instagram_identity


def customer(scoped_id):
    return SimpleNamespace(instagram_scoped_id=scoped_id)


def test_no_candidates_does_not_match():
    assert select_instagram_identity([], "id-1") is None


def test_single_consistent_candidate_matches():
    found = customer("id-1")
    assert select_instagram_identity([found], "id-1") is found


def test_single_candidate_without_scoped_id_can_be_enriched():
    found = customer(None)
    assert select_instagram_identity([found], "id-1") is found


def test_conflicting_scoped_ids_are_not_linked():
    with pytest.raises(InstagramIdentityConflict, match="DIRECT_CUSTOMER_IDENTITY_CONFLICT"):
        select_instagram_identity([customer("id-2")], "id-1")


def test_multiple_candidates_are_never_selected_by_order():
    with pytest.raises(InstagramIdentityConflict, match="DIRECT_CUSTOMER_IDENTITY_CONFLICT"):
        select_instagram_identity([customer("id-1"), customer("id-2")], "id-1")


def test_conflict_returns_http_409():
    from app.api.v1.direct_customer_automation import _http_error
    from app.services.direct_customer_automation_service import DirectCustomerAutomationError

    error = _http_error(DirectCustomerAutomationError("DIRECT_CUSTOMER_IDENTITY_CONFLICT"))
    assert error.status_code == 409
    assert error.detail == "DIRECT_CUSTOMER_IDENTITY_CONFLICT"


def test_inbound_conflict_is_contained_and_reported():
    from contextlib import nullcontext
    from app.integrations.meta_instagram.services.inbound_message_service import InstagramInboundMessageService
    from app.services.direct_customer_automation_service import DirectCustomerAutomationError

    class Automation:
        def ensure_from_inbound_order_intent(self, *_args):
            raise DirectCustomerAutomationError("DIRECT_CUSTOMER_IDENTITY_CONFLICT")

    service = object.__new__(InstagramInboundMessageService)
    service.db = SimpleNamespace(begin_nested=lambda: nullcontext())
    service.customer_automation = Automation()
    conversation = SimpleNamespace(id="conversation", provider_sync_status=None, linked_customer_id=None)
    service._ensure_customer_safe("workspace", conversation, "order")
    assert conversation.provider_sync_status == "CUSTOMER_IDENTITY_CONFLICT"
    assert conversation.linked_customer_id is None


def test_direct_matching_lock_serializes_workspace_on_postgres():
    import os
    from uuid import uuid4
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from app.repositories.customer_repository import CustomerRepository

    url = os.getenv("DATABASE_URL", "")
    if not url.startswith("postgresql"):
        pytest.skip("requires disposable PostgreSQL")
    engine = create_engine(url)
    workspace = uuid4()
    try:
        with Session(engine) as first, Session(engine) as second:
            assert CustomerRepository(first).try_lock_direct_matching(workspace)
            assert not CustomerRepository(second).try_lock_direct_matching(workspace)
            assert CustomerRepository(second).try_lock_direct_matching(uuid4())
            first.rollback()
            assert CustomerRepository(second).try_lock_direct_matching(workspace)
            second.rollback()
    finally:
        engine.dispose()


def test_conversation_nowait_keeps_outer_transaction_usable_on_postgres():
    import os
    from uuid import uuid4
    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import Session
    from app.models.workspace import Workspace
    from app.models.ai_direct import DirectConversation
    from app.repositories.ai_direct_repository import DirectConversationBusy, DirectConversationRepository

    url = os.getenv("DATABASE_URL", "")
    if os.getenv("SELLORA_DISPOSABLE_DATABASE") != "1" or not url.startswith("postgresql"):
        pytest.skip("requires explicitly disposable PostgreSQL")
    engine = create_engine(url)
    workspace_id = conversation_id = None
    try:
        with Session(engine) as seed:
            workspace = Workspace(name="Synthetic identity test", slug=uuid4().hex)
            seed.add(workspace)
            seed.flush()
            conversation = DirectConversation(workspace_id=workspace.id)
            seed.add(conversation)
            seed.commit()
            workspace_id, conversation_id = workspace.id, conversation.id
        with Session(engine) as first, Session(engine) as second:
            assert DirectConversationRepository(first).get_for_update_nowait(workspace_id, conversation_id)
            with pytest.raises(DirectConversationBusy):
                DirectConversationRepository(second).get_for_update_nowait(workspace_id, conversation_id)
            assert second.scalar(select(1)) == 1
            first.rollback()
            assert DirectConversationRepository(second).get_for_update_nowait(workspace_id, conversation_id)
            second.rollback()
    finally:
        if workspace_id is not None:
            with Session(engine) as cleanup:
                conversation = cleanup.get(DirectConversation, conversation_id)
                if conversation:
                    cleanup.delete(conversation)
                workspace = cleanup.get(Workspace, workspace_id)
                if workspace:
                    cleanup.delete(workspace)
                cleanup.commit()
        engine.dispose()
