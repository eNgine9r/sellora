from app.integrations.nova_poshta_client import NovaPoshtaClient


def test_provider_rejection_code_preserves_actionable_detail_without_secrets() -> None:
    client = NovaPoshtaClient("synthetic-secret-api-key")

    code = client._safe_rejection_code(
        {
            "errors": [
                "Recipient phone 380990511918, ref 0d545f52-e1c2-11e3-8c4a-0050568002cf and synthetic-secret-api-key are invalid"
            ]
        }
    )

    assert code.startswith("NOVA_POSHTA_PROVIDER_REJECTED::Recipient phone")
    assert "synthetic-secret-api-key" not in code
    assert "380990511918" not in code
    assert "0d545f52-e1c2-11e3-8c4a-0050568002cf" not in code
    assert "[VALUE]" in code
    assert "[REDACTED]" in code
    assert len(code) <= 120


def test_provider_rejection_code_falls_back_when_provider_has_no_detail() -> None:
    client = NovaPoshtaClient("synthetic-secret-api-key")

    assert client._safe_rejection_code({}) == "NOVA_POSHTA_PROVIDER_REJECTED"
