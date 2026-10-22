import pytest

from scripts.reconcile_nova_archive import ARCHIVE_SKU, PHONE_RE, normalize_phone, retrieve_complete_month


def test_archive_pagination_consumes_every_page_not_just_first_hundred():
    class Client:
        def __init__(self):
            self.pages = []
        def _call(self, model, method, args):
            assert (model, method) == ("InternetDocument", "getDocumentList")
            page = int(args["Page"])
            self.pages.append(page)
            start, size = ((0, 100) if page == 1 else (100, 44))
            return {
                "data": [{"IntDocNumber": "20" + f"{idx:012d}"} for idx in range(start, start+size)],
                "info": {"totalCount": 144},
            }
    client = Client()
    assert len(retrieve_complete_month(client, 2026, 5)) == 144
    assert client.pages == [1, 2]


def test_missing_page_fails_closed():
    class Client:
        def _call(self, model, method, args):
            return {
                "data": ([{"IntDocNumber": "20" + f"{i:012d}"} for i in range(100)]
                         if args["Page"] == "1" else []),
                "info": {"totalCount": 120},
            }
    with pytest.raises(RuntimeError, match="INCOMPLETE"):
        retrieve_complete_month(Client(), 2026, 5)


def test_formatted_phones_in_direct_match_one_normalized_number():
    phrases = [
        "+38 (067) 123-45-67",
        "0 67 123 45 67",
        "0671234567",
        "380671234567",
    ]
    for text in phrases:
        matches = PHONE_RE.findall(text)
        assert matches
        assert any(normalize_phone(x) == "+380671234567" for x in matches)


def test_14_digit_ttn_is_not_parsed_as_phone():
    assert PHONE_RE.findall("ТТН 20451234567890") == []


def test_archive_unknown_product_has_dedicated_sku():
    assert ARCHIVE_SKU == "NP-ARCHIVE-OTHER"
