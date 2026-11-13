"""Enroll or remove an operator's TOTP factor from a trusted terminal."""

import argparse
import base64
import re
import secrets
import sys
from datetime import UTC, datetime
from getpass import getpass
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError

from app.auth.password import verify_password
from app.database.session import SessionLocal
from app.models.platform_admin import PlatformAuditEvent
from app.repositories.platform_admin_repository import PlatformAuditRepository, PlatformGrantRepository
from app.repositories.platform_mfa_repository import PlatformMfaRepository
from app.repositories.user_repository import UserRepository
from app.services.platform_mfa_service import PlatformMfaError, matching_step, platform_mfa_cipher


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("enroll", "remove"))
    parser.add_argument("--operator", required=True, type=UUID)
    parser.add_argument("--approval-ref", required=True)
    args = parser.parse_args()
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        parser.error("A private interactive terminal is required")
    if not re.fullmatch(r"[A-Z0-9][A-Z0-9_-]{0,63}", args.approval_ref):
        parser.error("A valid approval reference is required")

    password = getpass("Operator password: ")
    try:
        with SessionLocal() as db:
            user = UserRepository(db).get_by_id(args.operator)
            grant = PlatformGrantRepository(db).get(args.operator)
            if not user or not user.is_active or not grant or grant.revoked_at is not None:
                parser.exit(1, "Active operator required.\n")
            if not verify_password(password, user.password_hash):
                parser.exit(1, "Operator authentication failed.\n")
            role = grant.role

        seed = encrypted_seed = step = None
        if args.action == "enroll":
            cipher = platform_mfa_cipher()
            seed = secrets.token_bytes(20)
            print("Add a time-based entry in your authenticator (6 digits, 30 seconds, SHA-1).")
            print("Setup key:", base64.b32encode(seed).decode())
            code = getpass("Authenticator code: ")
            step = matching_step(seed, code, datetime.now(UTC))
            if step is None:
                parser.exit(1, "Invalid authenticator code. No changes made.\n")
            encrypted_seed = cipher.encrypt(seed)

        with SessionLocal.begin() as db:
            grants = PlatformGrantRepository(db)
            grants.lock_changes()
            grant = grants.get(args.operator)
            user = UserRepository(db).get_by_id(args.operator)
            if not grant or grant.revoked_at is not None or grant.role != role or not user or not user.is_active:
                parser.exit(1, "Active operator required.\n")
            if not verify_password(password, user.password_hash):
                parser.exit(1, "Operator authentication failed.\n")
            repository = PlatformMfaRepository(db)
            if encrypted_seed is None:
                repository.delete_factor(args.operator)
            else:
                repository.replace_factor(args.operator, encrypted_seed, step)
            PlatformAuditRepository(db).add(PlatformAuditEvent(
                actor_user_id=args.operator, actor_role=role, action=f"MFA_{args.action.upper()}",
                outcome="ALLOWED", approval_ref=args.approval_ref,
            ))
    except (SQLAlchemyError, PlatformMfaError):
        parser.exit(1, "Platform MFA operation unavailable.\n")
    print("Platform MFA operation recorded.")


if __name__ == "__main__":
    main()
