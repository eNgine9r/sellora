"""Manage platform grants from a trusted operator terminal."""

import argparse
from getpass import getpass
import sys
from uuid import UUID

from app.database.session import SessionLocal
from app.models.platform_admin import PlatformRole
from app.services.platform_grant_service import PlatformGrantService


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("bootstrap", "grant", "revoke"))
    parser.add_argument("--actor", required=True, type=UUID)
    parser.add_argument("--target", required=True, type=UUID)
    parser.add_argument("--approval-ref", required=True)
    parser.add_argument("--role", choices=list(PlatformRole), type=PlatformRole)
    args = parser.parse_args()
    if (args.action == "grant") != (args.role is not None):
        parser.error("--role is required for grant only")
    if not sys.stdin.isatty():
        parser.error("An interactive terminal is required")
    with SessionLocal() as db:
        try:
            PlatformGrantService(db).change(
                actor_id=args.actor, target_id=args.target, password=getpass("Operator password: "),
                action=args.action.upper(), approval_ref=args.approval_ref, role=args.role,
            )
        except (ValueError, PermissionError) as exc:
            parser.exit(1, f"{exc}\n")
    print("Platform grant operation recorded.")


if __name__ == "__main__":
    main()
