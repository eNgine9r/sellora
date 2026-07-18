from app.integrations.meta_ads.token_crypto import MetaTokenCryptoError, decrypt_token, encrypt_token
from app.core.config import get_settings


def encrypt_instagram_token(raw_token: str) -> tuple[str, str | None, str]:
    settings = get_settings()
    if not settings.meta_token_encryption_key:
        raise MetaTokenCryptoError("META_TOKEN_ENCRYPTION_NOT_CONFIGURED")
    return encrypt_token(raw_token, settings.meta_token_encryption_key), None, settings.meta_token_encryption_key_version


def decrypt_instagram_token(ciphertext: str) -> str:
    settings = get_settings()
    if not settings.meta_token_encryption_key:
        raise MetaTokenCryptoError("META_TOKEN_ENCRYPTION_NOT_CONFIGURED")
    return decrypt_token(ciphertext, settings.meta_token_encryption_key)
