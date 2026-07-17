from app.services.import_pilot_safe_service import (
    formula_injection_issues,
    is_formula_injection_risk,
)


def test_formula_like_text_is_rejected() -> None:
    for value in ("=SUM(A1:A2)", "+CMD", "-CMD", "@SUM(A1:A2)"):
        assert is_formula_injection_risk(value) is True


def test_normal_phone_and_signed_numbers_are_allowed() -> None:
    for value in ("+380501234567", "-12.50", "+12", "ordinary text"):
        assert is_formula_injection_risk(value) is False


def test_formula_issue_contains_row_and_field_without_losing_context() -> None:
    issues = formula_injection_issues(
        [
            {"Name": "Safe", "Phone": "+380501234567"},
            {"Name": "=2+2", "Phone": "+380501234568"},
        ],
        {"name": "Name", "phone": "Phone"},
    )

    assert len(issues) == 1
    assert issues[0].row_number == 3
    assert issues[0].field == "name"
    assert issues[0].severity == "ERROR"
    assert "Formula-prefixed" in issues[0].message
