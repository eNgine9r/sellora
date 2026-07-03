from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings


class MetaTokenCryptoError(ValueError):
    """Raised for safe Meta token encryption/decryption failures."""


def _resolve_key(encryption_key: str | None = None) -> bytes:
    key = encryption_key or get_settings().meta_token_encryption_key
    if not key:
        raise MetaTokenCryptoError("Meta token encryption key is not configured.")
    try:
        return key.encode("utf-8")
    except Exception as exc:
        raise MetaTokenCryptoError("Meta token encryption key is invalid.") from exc


def _fernet(encryption_key: str | None = None) -> Fernet:
    try:
        return Fernet(_resolve_key(encryption_key))
    except MetaTokenCryptoError:
        raise
    except Exception as exc:
        raise MetaTokenCryptoError("Meta token encryption key is invalid.") from exc


def encrypt_token(raw_token: str, encryption_key: str | None = None) -> str:
    """Encrypt a server-side Meta token without logging or exposing raw material."""
    if not raw_token:
        raise MetaTokenCryptoError("Meta token value is required for encryption.")
    try:
        return _fernet(encryption_key).encrypt(raw_token.encode("utf-8")).decode("utf-8")
    except MetaTokenCryptoError:
        raise
    except Exception as exc:
        raise MetaTokenCryptoError("Meta token encryption failed.") from exc


def decrypt_token(encrypted_token: str, encryption_key: str | None = None) -> str:
    """Decrypt a server-side Meta token for backend-only use."""
    if not encrypted_token:
        raise MetaTokenCryptoError("Encrypted Meta token value is required for decryption.")
    try:
        return _fernet(encryption_key).decrypt(encrypted_token.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise MetaTokenCryptoError("Encrypted Meta token value is invalid.") from exc
    except MetaTokenCryptoError:
        raise
    except Exception as exc:
        raise MetaTokenCryptoError("Meta token decryption failed.") from exc
