#!/usr/bin/env python3
from __future__ import annotations

import os
import re
from urllib.parse import urlparse

from playwright.sync_api import TimeoutError

from staging_browser_mobile_qa import (
    QaRun,
    SCENARIOS,
    SHOTS,
    VIEWPORTS,
    sync_playwright,
)

FIXTURE_MARKER = "QA-8A1-BROWSER-FINAL"
FIXTURE_CUSTOMER = "QA-8A1-BROWSER-FINAL Customer"
FIXTURE_ORDER = "ORD-QA-BROWSER-20260713"
WORKSPACE_B_NAME = "Sellora QA — Browser B 20260713"


class FinalQaRun(QaRun):
    def __init__(self) -> None:
        super().__init__()
        self.second_workspace = os.environ.get("STAGING_SECOND_WORKSPACE_ID", "").strip()
        self.frontend_host = urlparse(self.frontend).netloc

    def core_url(self, url: str) -> bool:
        parsed = urlparse(url)
        path = parsed.path
        if path.startswith("/_next/static") or path.startswith("/_next/image"):
            return False
        if path.endswith(("/favicon.ico", "/robots.txt", "/manifest.json")):
            return False
        return parsed.netloc == self.frontend_host or path.startswith("/api/v1/")

    def login(self, page, viewport: str) -> dict:
        page.goto(f"{self.frontend}/login", wait_until="domcontentloaded", timeout=45000)
        self.wait(page)
        page.screenshot(path=str(SHOTS / f"{viewport}-login.png"), full_page=False)
        page.evaluate(
            "workspaceId => localStorage.setItem('sellora.current_workspace_id', workspaceId)",
            self.qa_workspace,
        )
        page.locator('input[type="email"], input[autocomplete="email"]').first.fill(
            self.email, timeout=10000
        )
        page.locator('input[type="password"], input[autocomplete="current-password"]').first.fill(
            self.password, timeout=10000
        )
        page.get_by_role("button", name="Увійти", exact=True).click(timeout=10000)
        try:
            page.wait_for_url(re.compile(r".*/dashboard(?:\?.*)?$"), timeout=45000)
        except TimeoutError:
            self.finding("FAIL", viewport, "Login", "auth", f"Login did not reach dashboard: {page.url}")
        self.wait(page)
        try:
            page.locator("[data-protected-shell-grid]").wait_for(state="visible", timeout=30000)
        except TimeoutError:
            self.finding("FAIL", viewport, "Login", "auth", "Protected shell did not become visible")

        current_workspace = page.evaluate("localStorage.getItem('sellora.current_workspace_id')")
        user = page.evaluate("JSON.parse(localStorage.getItem('sellora.current_user') || 'null')") or {}
        tokens_present = page.evaluate(
            "Boolean(localStorage.getItem('sellora.access_token') && localStorage.getItem('sellora.refresh_token'))"
        )
        status = "PASS"
        if "/login" in page.url or not tokens_present or current_workspace != self.qa_workspace:
            status = "FAIL"
            self.finding(
                "FAIL",
                viewport,
                "Login",
                "auth",
                f"url={page.url}; tokens={tokens_present}; workspace_match={current_workspace == self.qa_workspace}",
            )
        self.results.append(
            {
                "viewport": viewport,
                "scenario": "Login",
                "path": "/login",
                "status": status,
                "url": self.sanitize(page.url),
                "overflow": False,
                "screenshot": str(SHOTS / f"{viewport}-login.png"),
            }
        )
        return {"workspace": current_workspace, "user": user}

    def _open_workspace_panel(self, page, width: int):
        if width >= 768:
            page.locator("button.account-profile-trigger").click(timeout=10000)
            panel = page.locator('[role="menu"]').first
        else:
            page.locator('button[aria-controls="mobile-more-sheet"]').click(timeout=10000)
            panel = page.locator("#mobile-more-sheet")
        panel.wait_for(state="visible", timeout=10000)
        return panel

    def _switch_to(self, page, width: int, workspace_name: str, workspace_id: str) -> None:
        panel = self._open_workspace_panel(page, width)
        button = panel.get_by_role("button", name=re.compile(re.escape(workspace_name))).first
        button.click(timeout=10000)
        page.wait_for_function(
            "id => localStorage.getItem('sellora.current_workspace_id') === id",
            workspace_id,
            timeout=15000,
        )
        page.wait_for_timeout(1000)

    def workspace_switch(self, page, viewport: str, state: dict) -> None:
        width = page.viewport_size["width"]
        current = state.get("workspace")
        candidate = self.second_workspace
        if not candidate:
            self.finding("FAIL", viewport, "Workspace switch", "coverage", "Synthetic Workspace B ID is missing")
            return

        start = len(self.workspace_headers)
        self._switch_to(page, width, WORKSPACE_B_NAME, candidate)
        page.goto(f"{self.frontend}/leads", wait_until="domcontentloaded", timeout=45000)
        self.wait(page)
        body_b = page.locator("body").inner_text(timeout=10000)
        shot = SHOTS / f"{viewport}-workspace-b-leads.png"
        page.screenshot(path=str(shot), full_page=False)

        stale_marker = FIXTURE_MARKER in body_b or FIXTURE_ORDER in body_b
        headers = self.workspace_headers[start:]
        wrong_headers = [h for h in headers if h.get("workspace_id") == self.qa_workspace]
        has_b = any(h.get("workspace_id") == candidate for h in headers)
        status = "PASS"
        if stale_marker or wrong_headers or not has_b:
            status = "FAIL"
            self.finding(
                "FAIL",
                viewport,
                "Workspace switch",
                "workspace_stale_data",
                f"stale_marker={stale_marker}; wrong_A_headers={len(wrong_headers)}; has_B_header={has_b}",
            )
        self.results.append(
            {
                "viewport": viewport,
                "scenario": "Workspace switch A→B",
                "path": "/leads",
                "status": status,
                "url": self.sanitize(page.url),
                "overflow": False,
                "screenshot": str(shot),
            }
        )

        if current:
            self._switch_to(page, width, "Sellora QA — Sprint 8A.1", current)
            page.goto(f"{self.frontend}/leads", wait_until="domcontentloaded", timeout=45000)
            self.wait(page)
            body_a = page.locator("body").inner_text(timeout=10000)
            if FIXTURE_MARKER not in body_a:
                self.finding("FAIL", viewport, "Workspace switch", "workspace_restore", "Workspace A fixture was not restored")

    def inspect_page(self, page, viewport: str, scenario: str, path: str) -> None:
        super().inspect_page(page, viewport, scenario, path)
        result = self.results[-1]
        body = page.locator("body").inner_text(timeout=10000)
        required = None
        if scenario == "Leads":
            required = FIXTURE_MARKER
        elif scenario == "Customers":
            required = FIXTURE_CUSTOMER
        elif scenario == "Orders":
            required = FIXTURE_ORDER
        elif scenario == "Shipment draft":
            required = FIXTURE_ORDER
            if not ("Чернетка" in body or "DRAFT" in body):
                self.finding("FAIL", viewport, scenario, "fixture_visibility", "Shipment DRAFT status is not visible")
                result["status"] = "FAIL"
        if required and required not in body:
            self.finding("FAIL", viewport, scenario, "fixture_visibility", f"Required fixture not visible: {required}")
            result["status"] = "FAIL"

        filename = f"{viewport}-{scenario.lower().replace(' ', '-').replace('/', '-')}.jpg"
        shot = SHOTS / filename
        page.screenshot(path=str(shot), type="jpeg", quality=72, full_page=False)
        result["screenshot"] = str(shot)

    def mobile_drawer(self, page, viewport: str, width: int) -> None:
        if width >= 1024:
            return
        try:
            page.locator("button:has(svg.lucide-menu)").first.click(timeout=10000)
            dialog = page.locator('[role="dialog"][aria-modal="true"]').first
            dialog.wait_for(state="visible", timeout=10000)
            text = dialog.inner_text(timeout=10000)
            status = "PASS" if "Панель" in text and "Налаштування" in text else "FAIL"
            if status == "FAIL":
                self.finding("FAIL", viewport, "Mobile drawer", "navigation", "Expected navigation labels are missing")
            shot = SHOTS / f"{viewport}-mobile-drawer.jpg"
            page.screenshot(path=str(shot), type="jpeg", quality=72, full_page=False)
            self.results.append(
                {
                    "viewport": viewport,
                    "scenario": "Mobile drawer",
                    "path": "UI",
                    "status": status,
                    "url": self.sanitize(page.url),
                    "overflow": False,
                    "screenshot": str(shot),
                }
            )
            page.mouse.click(width - 4, 90)
            dialog.wait_for(state="hidden", timeout=10000)
        except Exception as exc:
            self.finding("FAIL", viewport, "Mobile drawer", "navigation", repr(exc))

    def logout(self, page, viewport: str) -> None:
        width = page.viewport_size["width"]
        try:
            panel = self._open_workspace_panel(page, width)
            panel.get_by_role("button", name="Вийти", exact=True).click(timeout=10000)
            page.wait_for_url(re.compile(r".*/login(?:\?.*)?$"), timeout=20000)
            state = page.evaluate(
                """() => ({
                    access: localStorage.getItem('sellora.access_token'),
                    refresh: localStorage.getItem('sellora.refresh_token'),
                    user: localStorage.getItem('sellora.current_user'),
                    workspace: localStorage.getItem('sellora.current_workspace_id')
                })"""
            )
            ok = all(value is None for value in state.values())
            if not ok:
                self.finding("FAIL", viewport, "Logout", "auth", "Auth storage was not fully cleared")
            self.results.append(
                {
                    "viewport": viewport,
                    "scenario": "Logout",
                    "path": "UI",
                    "status": "PASS" if ok else "FAIL",
                    "url": self.sanitize(page.url),
                    "overflow": False,
                }
            )
        except Exception as exc:
            self.finding("FAIL", viewport, "Logout", "auth", repr(exc))

    def run_viewport(self, browser, name: str, width: int, height: int) -> None:
        refresh_start = self.refresh_count
        context = browser.new_context(
            viewport={"width": width, "height": height},
            is_mobile=width < 768,
            has_touch=width < 768,
            locale="uk-UA",
            timezone_id="Europe/Kyiv",
            color_scheme="dark",
        )
        page = context.new_page()
        self.watch(page, name)
        try:
            state = self.login(page, name)
            self.mobile_drawer(page, name, width)
            self.workspace_switch(page, name, state)
            for scenario, path in SCENARIOS:
                self.inspect_page(page, name, scenario, path)
            refresh_delta = self.refresh_count - refresh_start
            if refresh_delta > 2:
                self.finding("FAIL", name, "Global", "refresh_token_loop", f"Refresh requests in viewport: {refresh_delta}")
            self.logout(page, name)
        except Exception as exc:
            self.finding("FAIL", name, "Global", "runner_exception", repr(exc))
            try:
                page.screenshot(path=str(SHOTS / f"{name}-runner-exception.png"), full_page=True)
            except Exception:
                pass
        finally:
            context.close()


if __name__ == "__main__":
    missing = [
        key
        for key in [
            "STAGING_FRONTEND_URL",
            "STAGING_OWNER_EMAIL",
            "STAGING_OWNER_PASSWORD",
            "STAGING_TEST_WORKSPACE_ID",
            "STAGING_SECOND_WORKSPACE_ID",
        ]
        if not os.environ.get(key, "").strip()
    ]
    if missing:
        raise SystemExit("Missing env vars: " + ", ".join(missing))
    decision = FinalQaRun().run()
    print("Browser/mobile QA decision:", decision)
    raise SystemExit(0 if decision == "PASS" else 1)
