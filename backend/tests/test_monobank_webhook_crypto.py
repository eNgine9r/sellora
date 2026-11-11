"""Signed webhook verification: tampered bodies or invalid signatures rejected."""
import base64

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa

from app.integrations.monobank.webhook_crypto import MonoWebhookVerificationError, verify_mono_webhook


def key_fixture():
    private = ec.generate_private_key(ec.SECP256R1())
    pem = private.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
    return private, pem


def test_signature_validates_exact_raw_body_bytes():
    private, pem = key_fixture()
    body = b'{"invoiceId":"demo001","status":"success"}'
    signature = base64.b64encode(private.sign(body, ec.ECDSA(hashes.SHA256()))).decode()
    assert verify_mono_webhook(body=body, signature_b64=signature, public_key_pem=pem)
    assert not verify_mono_webhook(body=body + b" ", signature_b64=signature, public_key_pem=pem)
    assert not verify_mono_webhook(body=body.replace(b"success", b"failure"), signature_b64=signature, public_key_pem=pem)


def test_foreign_key_cannot_verify_valid_signed_message():
    private, pem = key_fixture()
    other, _ = key_fixture()
    body = b"test"
    signature = base64.b64encode(other.sign(body, ec.ECDSA(hashes.SHA256()))).decode()
    assert not verify_mono_webhook(body=body, signature_b64=signature, public_key_pem=pem)


@pytest.mark.parametrize("body", [b"", b"x" * 65537])
def test_body_bounds(body):
    _, pem = key_fixture()
    with pytest.raises(MonoWebhookVerificationError):
        verify_mono_webhook(body=body, signature_b64="MDAwMDAwMDAwMDAwMDA=", public_key_pem=pem)


def test_rsa_key_rejected():
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = private.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
    with pytest.raises(MonoWebhookVerificationError):
        verify_mono_webhook(body=b"{}", signature_b64=base64.b64encode(b"invalid signature").decode(), public_key_pem=pem)
