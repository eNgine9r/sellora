"""ECDSA/SHA256 webhook verification for a bank-authenticated public key.

Use raw request bytes. Never parse/re-serialize before verification.
Public key must be obtained and pinned from the authentic bank API, not from
a webhook payload or a user-supplied URL. Verification is not bank settlement;
always re-fetch invoice state and deduplicate before any financial mutation.
"""
from base64 import b64decode, binascii
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec


class MonoWebhookVerificationError(ValueError):
    """Safe, non-sensitive validation failure."""


def verify_mono_webhook(*, body: bytes, signature_b64: str, public_key_pem: bytes) -> bool:
    if not isinstance(body, bytes) or not 0 < len(body) <= 65536:
        raise MonoWebhookVerificationError("Invalid body size")
    if not isinstance(signature_b64, str) or not 8 <= len(signature_b64) <= 256:
        raise MonoWebhookVerificationError("Invalid signature length")
    if not isinstance(public_key_pem, bytes) or len(public_key_pem) > 8192:
        raise MonoWebhookVerificationError("Invalid bank public key")
    try:
        signature = b64decode(signature_b64, validate=True)
        key = serialization.load_pem_public_key(public_key_pem)
        if not isinstance(key, ec.EllipticCurvePublicKey):
            raise MonoWebhookVerificationError("Unexpected bank key type")
        key.verify(signature, body, ec.ECDSA(hashes.SHA256()))
        return True
    except (ValueError, TypeError, binascii.Error, InvalidSignature) as exc:
        if isinstance(exc, MonoWebhookVerificationError):
            raise
        return False
