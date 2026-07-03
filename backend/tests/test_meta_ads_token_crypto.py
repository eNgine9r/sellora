from __future__ import annotations

from cryptography.fernet import Fernet

from app.integrations.meta_ads.token_crypto import MetaTokenCryptoError, decrypt_token, encrypt_token


def test_encrypts_and_decrypts_synthetic_token_without_plaintext() -> None:
    key = Fernet.generate_key().decode("utf-8")
    raw_token = "synthetic_meta_token_for_test_only"

    encrypted = encrypt_token(raw_token, key)

    assert encrypted != raw_token
    assert raw_token not in encrypted
    assert decrypt_token(encrypted, key) == raw_token


def test_missing_key_and_invalid_ciphertext_use_safe_errors() -> None:
    raw_token = "synthetic_meta_token_for_test_only"

    try:
        encrypt_token(raw_token, None)
    except MetaTokenCryptoError as exc:
        assert raw_token not in str(exc)
        assert "not configured" in str(exc)
    else:
        raise AssertionError("missing encryption key should fail safely")

    key = Fernet.generate_key().decode("utf-8")
    try:
        decrypt_token("not-a-valid-ciphertext", key)
    except MetaTokenCryptoError as exc:
        assert "not-a-valid-ciphertext" not in str(exc)
        assert "invalid" in str(exc)
    else:
        raise AssertionError("invalid ciphertext should fail safely")
