import pytest

from app.utils.phone import PhoneNormalizationError, format_ua_phone_for_display, normalize_ua_phone, to_nova_poshta_phone


@pytest.mark.parametrize("raw", ["0671234567", "+380671234567", "380671234567", "067 123 45 67", "(067) 123-45-67"])
def test_normalize_ua_phone_valid_matrix(raw: str) -> None:
    assert normalize_ua_phone(raw) == "+380671234567"
    assert to_nova_poshta_phone(normalize_ua_phone(raw) or "") == "380671234567"


@pytest.mark.parametrize("raw", ["text", "067123", "123456789012", "+380ABC123456", "++380671234567", "00380671234567"])
def test_normalize_ua_phone_invalid_matrix(raw: str) -> None:
    with pytest.raises(PhoneNormalizationError):
        normalize_ua_phone(raw)


def test_optional_blank_phone_becomes_none_and_display_is_ukrainian_friendly() -> None:
    assert normalize_ua_phone(" ") is None
    assert format_ua_phone_for_display("+380671234567") == "+380 67 123 45 67"
