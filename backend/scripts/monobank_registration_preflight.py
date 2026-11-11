"""OFFLINE preflight for monobank provider registration.

This script NEVER uses network, signatures, private keys or bank tokens.
Only run after the bank confirms the applicant's eligibility and the provider
registration protocol. Output contains contact PII; do not commit to GitHub.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec


REQUIRED = ("name", "description", "contactPerson", "phone", "email")
FORBIDDEN = frozenset({
    "privatekey", "private_key", "xtoken", "x-token", "token",
    "password", "secret", "personaltoken", "iban", "cardpan",
})
MAIL = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
PHONE = re.compile(r"^\+?[0-9]{10,15}$")


class PreflightError(ValueError):
    pass


def _non_placeholder(name: str, value: Any) -> str:
    if not isinstance(value, str):
        raise PreflightError(f"{name} must be text")
    item = value.strip()
    if not item or item != value or any(x in item.lower() for x in ("[", "]", "заповн", "example", "placeholder")):
        raise PreflightError(f"{name} is missing or placeholder")
    if len(item) > 1000 or any(c in item for c in ("\0", "\r", "\n")):
        raise PreflightError(f"{name} length/characters invalid")
    return item


def _image_bytes(image: bytes) -> bytes:
    if len(image) > 512_000 or len(image) < 64:
        raise PreflightError("Logo must be 64 bytes to 500 KiB")
    if not (image.startswith(b"\x89PNG\r\n\x1a\n") or image[:3] == b"\xff\xd8\xff"):
        raise PreflightError("Logo must be PNG or JPEG")
    return image


def _public_key_bytes(pem: bytes) -> bytes:
    if len(pem) > 8192 or not pem.startswith(b"-----BEGIN PUBLIC KEY-----"):
        raise PreflightError("Expected PEM X.509 public key, not private key")
    try:
        key = serialization.load_pem_public_key(pem)
    except (ValueError, TypeError) as exc:
        raise PreflightError("Invalid public key") from exc
    if not isinstance(key, ec.EllipticCurvePublicKey) or not isinstance(key.curve, ec.SECP256K1):
        raise PreflightError("Bank provider public key must be secp256k1")
    return pem


def build_registration_body(profile: dict[str, Any], public_key_pem: bytes, logo: bytes) -> dict[str, str]:
    if not isinstance(profile, dict):
        raise PreflightError("Expected JSON object")
    forbidden_found = [
        name for name in profile
        if str(name).replace("-", "").replace("_", "").lower() in
        {f.replace("-", "").replace("_", "") for f in FORBIDDEN}
    ]
    if forbidden_found:
        raise PreflightError("Profile contains forbidden banking secret field")
    if set(profile) != set(REQUIRED):
        missing = set(REQUIRED) - set(profile)
        extra = set(profile) - set(REQUIRED)
        raise PreflightError("Incorrect profile fields: missing=" + ",".join(sorted(missing)) +
                             "; extra=" + ",".join(sorted(extra)))
    values = {name: _non_placeholder(name, profile[name]) for name in REQUIRED}
    if not PHONE.fullmatch(values["phone"]):
        raise PreflightError("phone must contain 10-15 digits, optional leading +")
    if not MAIL.fullmatch(values["email"]):
        raise PreflightError("Invalid email")
    return {
        "pubkey": base64.b64encode(_public_key_bytes(public_key_pem)).decode("ascii"),
        "name": values["name"],
        "description": values["description"],
        "contactPerson": values["contactPerson"],
        "phone": values["phone"],
        "email": values["email"],
        "logo": base64.b64encode(_image_bytes(logo)).decode("ascii"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Offline monobank provider registration preflight; never calls the bank")
    parser.add_argument("--profile", required=True, type=Path, help="Private locally filled profile JSON")
    parser.add_argument("--public-key", required=True, type=Path, help="Public secp256k1 key in PEM")
    parser.add_argument("--logo", required=True, type=Path, help="Approved small PNG/JPEG logo")
    parser.add_argument("--output", type=Path, help="Explicit output JSON outside source control")
    args = parser.parse_args()
    profile = json.loads(args.profile.read_text(encoding="utf-8"))
    body = build_registration_body(profile, args.public_key.read_bytes(), args.logo.read_bytes())
    if args.output is None:
        print("PROVIDER_REGISTRATION_PREFLIGHT_PASS; no file written; no network access")
        return
    # Require an explicit, new output path and create it with owner-only perms.
    out = args.output.resolve()
    if any(x in str(out) for x in ("/.git/", "/github/", "/node_modules/")):
        raise PreflightError("Refuse to write profile data into source control or package trees")
    fd = os.open(out, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as target:
            json.dump(body, target, ensure_ascii=False, separators=(",", ":"))
            target.write("\n")
    except BaseException:
        out.unlink(missing_ok=True)
        raise
    print("PROVIDER_REGISTRATION_BODY_READY; owner-only file written; never sent to bank")


if __name__ == "__main__":
    main()
