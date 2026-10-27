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
