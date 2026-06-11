from base64 import urlsafe_b64encode
from hashlib import sha256

from cryptography.fernet import Fernet

from app.core.config import get_settings


def _fernet() -> Fernet:
    key_material = get_settings().secret_key.encode("utf-8")
    return Fernet(urlsafe_b64encode(sha256(key_material).digest()))


def encrypt_secret(value: str) -> str:
    return _fernet().encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_secret(value: str) -> str:
    return _fernet().decrypt(value.encode("utf-8")).decode("utf-8")


def mask_secret(value: str | None) -> str | None:
    if not value:
        return None
    suffix = value[-4:] if len(value) >= 4 else value
    return f"**** **** **** {suffix}"
