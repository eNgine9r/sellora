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
