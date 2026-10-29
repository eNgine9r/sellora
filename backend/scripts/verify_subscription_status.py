#!/usr/bin/env python3
"""Read-only subscription release canary; supply existing access tokens via env.

No login, database access, provider calls, redirects or response-body logging.
Run with --require-denials for the complete OWNER/MANAGER/ANALYST/tenant check.
"""
from __future__ import annotations

import argparse
import json
import os
from collections.abc import Mapping
from urllib.error import HTTPError
from urllib.parse import urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from uuid import UUID

STATUSES = ("UNMANAGED", "PENDING", "TRIALING", "ACTIVE", "PAST_DUE", "CANCELED", "EXPIRED")
PREFIX = "SELLORA_CANARY_"
PATH = "/api/v1/workspaces/current/subscription"


class CanaryError(Exception):
    """Contains only a bounded check code, never server or configuration text."""


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def endpoint(value: str) -> str:
    try:
        parsed = urlsplit(value)
        valid = (
            parsed.scheme in {"http", "https"} and parsed.hostname and parsed.port != 0
            and parsed.username is None and parsed.password is None
            and not parsed.query and not parsed.fragment
            and parsed.path.rstrip("/") in {"", "/api/v1"}
            and (parsed.scheme == "https" or parsed.hostname in {"127.0.0.1", "localhost", "::1"})
            and not any(character.isspace() for character in value)
        )
    except ValueError:
        valid = False
    if not valid:
        raise CanaryError("invalid_api_url")
    return urlunsplit((parsed.scheme, parsed.netloc, PATH, "", ""))


def workspace(value: str, label: str) -> str:
    try:
        return str(UUID(value))
    except ValueError:
        raise CanaryError(f"invalid_{label}") from None


def get(
    url: str, workspace_id: str | None, token: str | None, *, read_body: bool = False,
) -> tuple[int, Mapping[str, str], object | None]:
    headers = {"Accept": "application/json"}
    if workspace_id:
        headers["X-Workspace-ID"] = workspace_id
    if token:
        headers["Authorization"] = "Bearer " + token
    try:
        with build_opener(NoRedirect()).open(Request(url, headers=headers, method="GET"), timeout=10) as response:
            payload = None
            if read_body and response.status == 200:
                raw = response.read(16385)
                if len(raw) > 16384:
                    raise CanaryError("owner_body_too_large")
                try:
                    payload = json.loads(raw)
                except (ValueError, UnicodeError):
                    raise CanaryError("owner_invalid_json") from None
            return response.status, response.headers, payload
    except HTTPError as exc:
        code = exc.code
        exc.close()
        return code, {}, None
    except CanaryError:
        raise
    except Exception:
        raise CanaryError("http_request_failed") from None


def run(expected_status: str, require_denials: bool) -> dict[str, object]:
    values = {name: os.getenv(PREFIX + name, "") for name in (
        "API_URL", "WORKSPACE_ID", "OWNER_TOKEN", "MANAGER_TOKEN", "ANALYST_TOKEN", "FOREIGN_WORKSPACE_ID",
    )}
    if not all(values[name] for name in ("API_URL", "WORKSPACE_ID", "OWNER_TOKEN")):
        raise CanaryError("missing_required_environment")
    if expected_status not in STATUSES:
        raise CanaryError("invalid_expected_status")
    if any(any(character.isspace() for character in values[role + "_TOKEN"])
           for role in ("OWNER", "MANAGER", "ANALYST")):
        raise CanaryError("invalid_token")
    url = endpoint(values["API_URL"])
    selected = workspace(values["WORKSPACE_ID"], "workspace_id")
    foreign = workspace(values["FOREIGN_WORKSPACE_ID"], "foreign_workspace_id") if values["FOREIGN_WORKSPACE_ID"] else None
    if foreign == selected:
        raise CanaryError("foreign_workspace_must_differ")
    skipped = [role.lower() + "_denied" for role in ("MANAGER", "ANALYST") if not values[role + "_TOKEN"]]
    if not foreign:
        skipped.append("foreign_workspace_denied")
    if require_denials and skipped:
        raise CanaryError("missing_denial_environment")

    code, headers, payload = get(url, selected, values["OWNER_TOKEN"], read_body=True)
    if code != 200:
        raise CanaryError(f"owner_http_{code}")
    if not isinstance(payload, dict):
        raise CanaryError("owner_invalid_payload")
    checks = {
        "workspace_match": payload.get("workspace_id") == selected,
        "expected_status": payload.get("status") == expected_status,
        "enforcement_disabled": payload.get("enforcement_enabled") is False,
        "current_term": payload.get("has_current_term") is (expected_status in {"ACTIVE", "TRIALING"}),
        "cache_no_store": "no-store" in {part.strip().lower() for part in headers.get("Cache-Control", "").split(",")},
    }
    if expected_status == "UNMANAGED":
        checks["no_automatic_enrollment"] = (
            all(payload.get(field) is None for field in ("plan_code", "current_period_start", "current_period_end"))
            and payload.get("cancel_at_period_end") is False
        )
    for name, passed in checks.items():
        if not passed:
            raise CanaryError(name)

    denials = [("unauthenticated_denied", selected, None, 401),
               ("missing_workspace_denied", None, values["OWNER_TOKEN"], 400)]
    denials.extend((role.lower() + "_denied", selected, values[role + "_TOKEN"], 403)
                   for role in ("MANAGER", "ANALYST") if values[role + "_TOKEN"])
    if foreign:
        denials.append(("foreign_workspace_denied", foreign, values["OWNER_TOKEN"], 403))
    for name, target, token, expected_code in denials:
        code, _, _ = get(url, target, token)
        if code != expected_code:
            raise CanaryError(f"{name}_http_{code}")
        checks[name] = True
    return {"result": "PASS", "expected_status": expected_status, "checks": list(checks), "skipped": skipped}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-status", default="UNMANAGED", metavar="STATUS", help=", ".join(STATUSES))
    parser.add_argument("--require-denials", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = run(args.expected_status, args.require_denials)
    except CanaryError as exc:
        result = {"result": "FAIL", "check": str(exc)}
    except Exception:
        result = {"result": "FAIL", "check": "unexpected_probe_error"}
    print(json.dumps(result))
    return 0 if result["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
