"""Bank-provider application preparation tests. No network or real credentials."""
import base64
import json
import os
import sys

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

from scripts.monobank_registration_preflight import (
    PreflightError, build_registration_body, main,
)


def profile():
    return {
        "name": "Заявник тестовий ФОП",
        "description": "Sellora CRM demo read only business account ledger after consent",
        "contactPerson": "Demo Test",
        "phone": "+380670000000",
        "email": "demo@mycompany.test",
    }


def make_key(curve=None):
    private = ec.generate_private_key(curve or ec.SECP256K1())
    return private.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )


def make_logo():
    return b"\xff\xd8\xff" + b"0" * 130


def test_complete_payload_has_exact_official_fields_only():
    pem = make_key()
    image = make_logo()
    data = build_registration_body(profile(), pem, image)
    assert set(data) == {"name", "description", "contactPerson", "phone", "email", "pubkey", "logo"}
    assert base64.b64decode(data["pubkey"]) == pem
    assert base64.b64decode(data["logo"]) == image
    assert "private" not in json.dumps(data).lower()


def test_incomplete_or_sensitive_profile_fails_closed():
    for bad in (
        {"name": "[PLACEHOLDER]"},
        {"email": "invalid@bad"},
        {"phone": "not-a-phone"},
        {"xtoken": "never"},
        {"secret": "never"},
    ):
        values = profile()
        values.update(bad)
        with pytest.raises(PreflightError):
            build_registration_body(values, make_key(), make_logo())


def test_provider_key_curve_and_private_key_rejected():
    with pytest.raises(PreflightError, match="secp256k1"):
        build_registration_body(profile(), make_key(ec.SECP256R1()), make_logo())
    private = ec.generate_private_key(ec.SECP256K1())
    private_pem = private.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    with pytest.raises(PreflightError, match="public"):
        build_registration_body(profile(), private_pem, make_logo())


@pytest.mark.parametrize("image", [b"", b"PDF" * 250, b"\x89PNG\r\n\x1a\n" + b"x" * 512001])
def test_logo_is_small_and_png_or_jpeg_only(image):
    with pytest.raises(PreflightError):
        build_registration_body(profile(), make_key(), image)


def test_cli_writes_owner_only_file_without_network(tmp_path, monkeypatch, capsys):
    p = tmp_path / "profile.json"
    key = tmp_path / "public.pem"
    logo = tmp_path / "logo.jpg"
    output = tmp_path / "registration-body.json"
    p.write_text(json.dumps(profile(), ensure_ascii=False), encoding="utf-8")
    key.write_bytes(make_key())
    logo.write_bytes(make_logo())
    monkeypatch.setattr(
        sys, "argv",
        ["monobank_registration_preflight.py", "--profile", str(p), "--public-key",
         str(key), "--logo", str(logo), "--output", str(output)],
    )
    main()
    assert output.exists()
    assert os.stat(output).st_mode & 0o777 == 0o600
    assert json.loads(output.read_text())["name"] == profile()["name"]
    assert "never sent" in capsys.readouterr().out
    with pytest.raises(FileExistsError):
        main()
