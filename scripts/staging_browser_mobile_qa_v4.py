#!/usr/bin/env python3
"""Browser-native Sprint 8A.1 QA entrypoint.

Fixture writes use the same browser network path and runtime API base as the
Sellora frontend. This avoids treating a GitHub Python-client route timeout as a
frontend browser defect while keeping the actual browser/network checks strict.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

MODULE_PATH = Path(__file__).with_name("staging_browser_mobile_qa_v2.py")
spec = importlib.util.spec_from_file_location("sellora_browser_qa_v2", MODULE_PATH)
if spec is None or spec.loader is None:
    raise SystemExit("Unable to load browser QA v2 module")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class BrowserNativeQa(module.BrowserQa):
    def __init__(self) -> None:
        super().__init__()
        self.runtime_api_base = ""

    def detect_runtime_api_base(self, page) -> str:
        detected = page.evaluate(
            """
            () => {
              const names = performance.getEntriesByType('resource').map((entry) => entry.name);
              const login = names.find((name) => name.includes('/auth/login'));
              if (!login) return '/api/v1';
              return login.replace(/\/auth\/login(?:\?.*)?$/, '');
            }
            """
        )
        return str(detected or "/api/v1").rstrip("/")

    def browser_api(self, page, method: str, endpoint: str, workspace_id: str, payload: dict | None = None) -> dict:
        result = page.evaluate(
            """
            async ({ apiBase, method, endpoint, workspaceId, payload }) => {
              const token = localStorage.getItem('sellora.access_token');
              const headers = {
                'Accept': 'application/json',
                'Authorization': `Bearer ${token}`,
                'X-Workspace-ID': workspaceId,
              };
              if (payload !== null) headers['Content-Type'] = 'application/json';
              try {
                const response = await fetch(`${apiBase}${endpoint}`, {
                  method,
                  headers,
                  body: payload === null ? undefined : JSON.stringify(payload),
                });
                const text = await response.text();
                let data = null;
                try { data = text ? JSON.parse(text) : null; } catch { data = { detail: text.slice(0, 300) }; }
                return { status: response.status, data };
              } catch (error) {
                return { status: 0, data: { detail: String(error) } };
              }
            }
            """,
            {
                "apiBase": self.runtime_api_base,
                "method": method,
                "endpoint": endpoint,
                "workspaceId": workspace_id,
                "payload": payload,
            },
        )
        return dict(result)

    def prepare_fixtures_browser(self, page) -> None:
        if self.fixture_ids:
            return
        self.runtime_api_base = self.detect_runtime_api_base(page)
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

    def cleanup_fixtures_browser(self, browser) -> None:
        if not self.fixture_ids or not self.access_token:
            return
        context = browser.new_context(viewport={"width": 1366, "height": 768})
        page = context.new_page()
        try:
            page.goto(f"{self.frontend}/login", wait_until="domcontentloaded", timeout=30000)
            page.evaluate(
                """({ token, workspaceId }) => {
                  localStorage.setItem('sellora.access_token', token);
                  localStorage.setItem('sellora.current_workspace_id', workspaceId);
                }""",
                {"token": self.access_token, "workspaceId": self.workspace_a},
            )
            for workspace_id, lead_id in self.fixture_ids:
                result = self.browser_api(page, "DELETE", f"/leads/{lead_id}", workspace_id, None)
                if result.get("status") not in (200, 204, 404):
                    self.finding("WARN", "global", "Cleanup", "fixture_cleanup", f"Lead cleanup HTTP {result.get('status')}")
        except Exception as exc:
            self.finding("WARN", "global", "Cleanup", "fixture_cleanup", repr(exc))
        finally:
            context.close()

    def run_viewport(self, browser, viewport: str, width: int, height: int) -> None:
        context = browser.new_context(
            viewport={"width": width, "height": height},
            is_mobile=width < 768,
            has_touch=width < 768,
        )
        page = context.new_page()
        self.watch(page, viewport)
        try:
            self.login(page, viewport, width)
            self.prepare_fixtures_browser(page)
            self.verify_workspace_isolation(page, viewport, width)
            for scenario, path in module.SCENARIOS:
                self.inspect_route(page, viewport, scenario, path)
            if self.refresh_by_viewport.get(viewport, 0) > 3:
                self.finding(
                    "FAIL",
                    viewport,
                    "Global",
                    "refresh_token_loop",
                    f"Refresh requests: {self.refresh_by_viewport[viewport]}",
                )
            self.logout(page, viewport, width)
        except Exception as exc:
            self.finding("FAIL", viewport, "Global", "runner_exception", repr(exc))
            try:
                page.screenshot(path=str(module.SHOTS / f"{viewport}-runner-exception.png"), full_page=True)
            except Exception:
                pass
        finally:
            context.close()

    def run(self) -> str:
        module.OUT.mkdir(parents=True, exist_ok=True)
        module.SHOTS.mkdir(parents=True, exist_ok=True)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                for viewport in module.VIEWPORTS:
                    self.run_viewport(browser, *viewport)
                self.cleanup_fixtures_browser(browser)
            finally:
                browser.close()
        return self.write_report()


if __name__ == "__main__":
    required = [
        "STAGING_FRONTEND_URL",
        "STAGING_OWNER_EMAIL",
        "STAGING_OWNER_PASSWORD",
        "STAGING_TEST_WORKSPACE_ID",
        "STAGING_SECOND_WORKSPACE_ID",
    ]
    missing = [name for name in required if not module.env(name)]
    if missing:
        print("Missing required browser QA inputs", file=sys.stderr)
        raise SystemExit(2)
    decision = BrowserNativeQa().run()
    print(f"Browser/mobile QA decision: {decision}")
    raise SystemExit(0 if decision == "PASS" else 1)
