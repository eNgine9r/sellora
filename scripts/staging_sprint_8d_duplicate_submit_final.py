#!/usr/bin/env python3
"""Final narrow Sprint 8D browser proof for inventory duplicate-submit protection."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

import httpx
from playwright.sync_api import sync_playwright

from staging_sprint_8d_browser_v2 import (
    BACKEND,
    FRONTEND,
    TIMEOUT,
    BrowserClosure,
)

OUT_DIR = Path("artifacts/sprint-8d-duplicate-submit")
REPORT_PATH = OUT_DIR / "duplicate-submit.json"
MD_PATH = OUT_DIR / "duplicate-submit.md"
SCREENSHOT_PATH = OUT_DIR / "duplicate-submit-final.png"


class FinalDuplicateSubmitProbe(BrowserClosure):
    def wait_environment(self) -> None:
        with httpx.Client(timeout=TIMEOUT, follow_redirects=True, headers={"Connection": "close"}) as client:
            health = client.get(BACKEND + "/health")
            frontend = client.get(FRONTEND + "/login")
        body: dict[str, Any] = health.json() if health.status_code == 200 else {}
        self.runtime = {
            "status": body.get("status"),
            "runtime_commit": body.get("runtime_commit"),
            "process_started_at": body.get("process_started_at"),
            "frontend_status": frontend.status_code,
            "frontend_url": FRONTEND,
        }
        ok = (
            health.status_code == 200
            and body.get("status") == "ok"
            and bool(body.get("runtime_commit"))
            and frontend.status_code == 200
        )
        self.check("A", "canonical frontend and backend are reachable", ok, self.runtime)
        if not ok:
            raise RuntimeError("Canonical staging environment is not ready")

    def capture_final_screenshot(self) -> None:
        assert self.owner is not None
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = self.context(browser, 1366, 768, "light")
            page = context.new_page()
            self.watch_page(page, "final-screenshot")
            try:
                page.goto(FRONTEND + "/inventory", wait_until="domcontentloaded", timeout=60000)
                self.wait_page(page)
                page.screenshot(path=str(SCREENSHOT_PATH), full_page=True)
            finally:
                context.close()
                browser.close()

    def write_final_report(self) -> str:
        failures = [item for item in self.checks if item.get("status") != "PASS"]
        blockers = [item for item in self.findings if item.get("severity") == "BLOCKER"]
        cleanup_ok = (
            self.cleanup.get("fixture_stock") == 0
            and self.cleanup.get("fixture_reserved") == 0
            and self.cleanup.get("fixture_visible") is False
            and self.cleanup.get("orders") == 0
            and self.cleanup.get("shipments") == 0
        )
        decision = "PASS" if not failures and not blockers and not self.safe_error and cleanup_ok else "FAIL"
        report = {
            "sprint": "8D",
            "phase": "final-canonical-duplicate-submit",
            "decision": decision,
            "runtime": self.runtime,
            "checks": self.checks,
            "findings": self.findings,
            "duplicate_submit": {
                "inventory_post_count": len(self.duplicate_post_urls),
                "expected_post_count": 1,
            },
            "cleanup": self.cleanup,
            "network": self.network,
            "browser_errors": {
                "console_count": len(self.console_errors),
                "page_error_count": len(self.page_errors),
                "request_failure_count": len(self.request_failures),
                "unexpected_http_count": len(self.unexpected_http),
                "cors_count": len(self.cors_errors),
            },
            "screenshot": SCREENSHOT_PATH.name if SCREENSHOT_PATH.exists() else None,
            "security": {
                "passwords_suppressed": True,
                "tokens_suppressed": True,
                "authorization_headers_suppressed": True,
                "customer_pii_synthetic": True,
                "provider_calls_suppressed": True,
            },
            "safe_error": self.safe_error,
        }
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        lines = [
            "# Sprint 8D final duplicate-submit proof",
            "",
            f"- Decision: **{decision}**",
            f"- Canonical frontend: `{FRONTEND}`",
            f"- Inventory POST count: {len(self.duplicate_post_urls)}",
            f"- Cleanup stock/reserved: {self.cleanup.get('fixture_stock')}/{self.cleanup.get('fixture_reserved')}",
            f"- Browser errors: {len(self.console_errors) + len(self.page_errors) + len(self.request_failures)}",
            "",
            "| Gate | Check | Status |",
            "|---|---|---|",
        ]
        lines.extend(f"| {item['gate']} | {item['name']} | {item['status']} |" for item in self.checks)
        MD_PATH.write_text("\n".join(lines), encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)
        return decision

    def run_final(self) -> int:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        try:
            self.wait_environment()
            self.login()
            self.setup_fixture()
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                try:
                    self.duplicate_submit(browser)
                finally:
                    browser.close()
        except Exception as exc:
            self.safe_error = str(exc)[:700]
            self.finding("BLOCKER", "final-duplicate-submit", "safe_error", self.safe_error)
        finally:
            if self.owner:
                self.cleanup_fixture()
                try:
                    self.capture_final_screenshot()
                except Exception as exc:
                    self.finding("WARN", "final-screenshot", "capture_error", repr(exc))
            self.final_browser_health()
        return 0 if self.write_final_report() == "PASS" else 1


if __name__ == "__main__":
    required = [
        "STAGING_FRONTEND_URL",
        "STAGING_API_URL",
        "STAGING_OWNER_EMAIL",
        "STAGING_OWNER_PASSWORD",
        "STAGING_TEST_WORKSPACE_ID",
    ]
    if any(not os.environ.get(name) for name in required):
        print("Missing required Sprint 8D final duplicate-submit input", file=sys.stderr)
        raise SystemExit(2)
    raise SystemExit(FinalDuplicateSubmitProbe().run_final())
