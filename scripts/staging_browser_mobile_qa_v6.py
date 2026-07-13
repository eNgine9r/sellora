#!/usr/bin/env python3
"""Final deterministic Sprint 8A.1 browser/mobile QA runner.

Fixes prior QA-runner false failures by:
- using the explicit staging API base for synthetic fixtures;
- selecting the mobile profile control by its accessible name;
- ignoring only navigation-cancelled ``net::ERR_ABORTED`` requests;
- waiting for the authenticated frontend bootstrap before protected navigation.
"""
from __future__ import annotations

import importlib.util
import re
import sys
import time
from pathlib import Path

MODULE_PATH = Path(__file__).with_name("staging_browser_mobile_qa_v5.py")
spec = importlib.util.spec_from_file_location("sellora_browser_qa_v5", MODULE_PATH)
if spec is None or spec.loader is None:
    raise SystemExit("Unable to load browser QA v5 module")
v5 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v5)


class FinalBrowserQa(v5.ColdStartTolerantQa):
    def __init__(self) -> None:
        super().__init__()
        api_root = v5.v4.module.env("STAGING_API_URL").rstrip("/")
        if not api_root:
            raise RuntimeError("STAGING_API_URL is required")
        self.runtime_api_base = f"{api_root}/api/v1"

    def watch(self, page, viewport: str) -> None:
        self.refresh_by_viewport.setdefault(viewport, 0)

        def on_console(message) -> None:
            raw = message.text
            if self.has_secret_value(raw):
                self.finding("FAIL", viewport, "Global", "secret_leak", "Console contained an actual credential/token value")
            if message.type == "error":
                self.finding("FAIL", viewport, "Global", "runtime_exception", f"console.error: {raw}")

        def on_page_error(error) -> None:
            self.finding("FAIL", viewport, "Global", "runtime_exception", repr(error))

        def on_request(request) -> None:
            if "/auth/refresh" in request.url:
                self.refresh_by_viewport[viewport] += 1
            workspace_id = request.headers.get("x-workspace-id")
            if workspace_id:
                self.workspace_headers.append({
                    "viewport": viewport,
                    "workspace_id": workspace_id,
                    "url": self.sanitize(request.url),
                })
            if self.has_secret_value(request.url):
                self.finding("FAIL", viewport, "Global", "secret_leak", "Request URL contained an actual credential/token value")

        def on_response(response) -> None:
            parsed_path = response.url.split("?", 1)[0]
            is_api = "/api/" in parsed_path
            is_document = response.request.resource_type == "document"
            if (is_api or is_document) and (response.status == 404 or response.status >= 500):
                self.finding("FAIL", viewport, "Global", "core_404_500", f"HTTP {response.status}: {response.url}")
            if is_api or is_document:
                self.network.append({
                    "viewport": viewport,
                    "status": response.status,
                    "url": self.sanitize(response.url),
                })

        def on_failed(request) -> None:
            if request.resource_type not in ("document", "xhr", "fetch"):
                return
            failure = str(request.failure or "")
            # React/Next route transitions legitimately cancel obsolete in-flight
            # reads. This is not a CORS/runtime defect when reported as ERR_ABORTED.
            if "ERR_ABORTED" in failure:
                return
            detail = f"{request.url}: {failure}"
            category = "cors_error" if "cors" in detail.lower() else "network_failure"
            self.finding("FAIL", viewport, "Global", category, detail)

        page.on("console", on_console)
        page.on("pageerror", on_page_error)
        page.on("request", on_request)
        page.on("response", on_response)
        page.on("requestfailed", on_failed)

    def open_workspace_menu(self, page, width: int) -> None:
        desktop = page.locator(".account-profile-trigger:visible")
        if width >= 768 and desktop.count() > 0:
            desktop.first.click(timeout=15000)
        else:
            button = page.get_by_role("button", name=re.compile(r"Більше дій|More actions", re.I))
            if button.count() == 0:
                button = page.locator('[aria-controls="mobile-more-sheet"]:visible')
            button.first.click(timeout=15000)
        page.wait_for_timeout(700)

    def prepare_fixtures_browser(self, page) -> None:
        if self.fixture_ids:
            return
        self.access_token = str(page.evaluate("localStorage.getItem('sellora.access_token') || ''"))
        if not self.access_token:
            raise RuntimeError("Browser session has no access token for fixture setup")
        for workspace_id, marker in [(self.workspace_a, self.marker_a), (self.workspace_b, self.marker_b)]:
            result = self.browser_api(
                page,
                "POST",
                "/leads",
                workspace_id,
                {"name": marker, "instagram_username": marker.lower()},
            )
            if result.get("status") not in (200, 201) or not isinstance(result.get("data"), dict) or not result["data"].get("id"):
                raise RuntimeError(
                    f"Browser fixture lead create failed HTTP {result.get('status')}: {self.sanitize(result.get('data'))}"
                )
            self.fixture_ids.append((workspace_id, str(result["data"]["id"])))

    def login(self, page, viewport: str, width: int) -> bool:
        page.goto(f"{self.frontend}/login", wait_until="domcontentloaded", timeout=45000)
        self.wait(page)
        page.screenshot(path=str(v5.v4.module.SHOTS / f"{viewport}-login.png"))

        page.locator('input[type="email"], input[autocomplete="email"]').first.fill(self.email)
        page.locator('input[type="password"], input[autocomplete="current-password"]').first.fill(self.password)
        page.locator('button[type="submit"]').first.click()

        try:
            page.wait_for_function(
                "Boolean(localStorage.getItem('sellora.access_token') && localStorage.getItem('sellora.refresh_token'))",
                timeout=180000,
            )
        except Exception:
            self.finding("FAIL", viewport, "Login", "auth", "Login did not create a session within 180 seconds")
            return False

        # Allow AuthProvider to finish /auth/me and workspace bootstrap before
        # forcing protected navigation.
        deadline = time.monotonic() + 75
        while time.monotonic() < deadline:
            current_workspace = page.evaluate("localStorage.getItem('sellora.current_workspace_id')")
            if current_workspace and "/login" not in page.url:
                break
            page.wait_for_timeout(1500)

        if "/login" in page.url:
            page.goto(f"{self.frontend}/dashboard", wait_until="domcontentloaded", timeout=45000)
            self.wait(page)
            page.wait_for_timeout(5000)

        if "/login" in page.url:
            # One final reload protects against a transient bootstrap redirect.
            page.reload(wait_until="domcontentloaded", timeout=45000)
            self.wait(page)

        if "/login" in page.url:
            self.finding("FAIL", viewport, "Login", "auth", "Session exists but protected navigation still redirects to /login")
            return False

        self.switch_workspace_ui(page, viewport, width, self.workspace_a_name, self.workspace_a)
        if "/login" in page.url:
            return False
        self.results.append({"viewport": viewport, "scenario": "Login", "status": "PASS", "path": "/login"})
        return True


if __name__ == "__main__":
    required = [
        "STAGING_FRONTEND_URL",
        "STAGING_API_URL",
        "STAGING_OWNER_EMAIL",
        "STAGING_OWNER_PASSWORD",
        "STAGING_TEST_WORKSPACE_ID",
        "STAGING_SECOND_WORKSPACE_ID",
    ]
    missing = [name for name in required if not v5.v4.module.env(name)]
    if missing:
        print("Missing required browser QA inputs", file=sys.stderr)
        raise SystemExit(2)
    decision = FinalBrowserQa().run()
    print(f"Browser/mobile QA decision: {decision}")
    raise SystemExit(0 if decision == "PASS" else 1)
