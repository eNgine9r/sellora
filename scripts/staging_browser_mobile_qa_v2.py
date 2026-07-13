#!/usr/bin/env python3
"""Deterministic Sprint 8A.1 browser/mobile QA for Sellora staging.

Uses synthetic OWNER credentials and two explicit QA workspaces only. Creates one
synthetic Lead marker in each QA workspace, validates the real UI workspace
switch against stale DOM/cache data, traverses protected routes at five
viewports, captures console/network evidence, performs UI logout, and archives
both fixture leads. Artifacts never contain passwords, tokens or auth headers.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

OUT = Path("artifacts/browser-mobile-qa")
SHOTS = OUT / "screenshots"
REPORT_JSON = OUT / "browser-mobile-qa-report.json"
REPORT_MD = OUT / "browser-mobile-qa-report.md"

VIEWPORTS = [
    ("desktop-1366x768", 1366, 768),
    ("mobile-375x812", 375, 812),
    ("mobile-390x844", 390, 844),
    ("mobile-430x932", 430, 932),
    ("tablet-768x1024", 768, 1024),
]

SCENARIOS = [
    ("Dashboard", "/dashboard"),
    ("Leads", "/leads"),
    ("Customers", "/customers"),
    ("Products", "/products"),
    ("Inventory", "/inventory"),
    ("Orders", "/orders"),
    ("Shipment draft", "/shipments"),
    ("Finance", "/finance"),
    ("Advertising", "/advertising"),
    ("Analytics", "/analytics"),
    ("Settings", "/settings"),
    ("Team", "/settings/team"),
]

VISIBLE_ERROR_PATTERNS = [
    re.compile(r"Application error", re.I),
    re.compile(r"Unhandled Runtime Error", re.I),
    re.compile(r"Something went wrong", re.I),
    re.compile(r"Internal Server Error", re.I),
]

TOKEN_PATTERNS = [
    re.compile(r"Bearer\s+[A-Za-z0-9._~+/=-]{20,}", re.I),
    re.compile(r"\beyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{12,}\b", re.I),
]


def env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def api_json(method: str, url: str, payload: dict | None = None, headers: dict | None = None) -> tuple[int, object]:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request_headers = {"Accept": "application/json", **(headers or {})}
    if payload is not None:
        request_headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=body, headers=request_headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=35) as response:
            raw = response.read().decode("utf-8")
            return response.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            parsed: object = json.loads(raw) if raw else None
        except json.JSONDecodeError:
            parsed = {"detail": raw[:300]}
        return exc.code, parsed


class BrowserQa:
    def __init__(self) -> None:
        self.frontend = env("STAGING_FRONTEND_URL").rstrip("/")
        self.api = env("STAGING_API_URL").rstrip("/")
        self.email = env("STAGING_OWNER_EMAIL")
        self.password = env("STAGING_OWNER_PASSWORD")
        self.workspace_a = env("STAGING_TEST_WORKSPACE_ID")
        self.workspace_b = env("STAGING_SECOND_WORKSPACE_ID")
        self.workspace_a_name = env("STAGING_TEST_WORKSPACE_NAME", "Sellora QA — Sprint 8A.1")
        self.workspace_b_name = env("STAGING_SECOND_WORKSPACE_NAME", "Sellora QA — Browser B 20260713")
        stamp = str(int(time.time()))
        self.marker_a = f"QA-BROWSER-A-{stamp}"
        self.marker_b = f"QA-BROWSER-B-{stamp}"
        self.fixture_ids: list[tuple[str, str]] = []
        self.findings: list[dict[str, str]] = []
        self.results: list[dict[str, object]] = []
        self.network: list[dict[str, object]] = []
        self.workspace_headers: list[dict[str, str]] = []
        self.refresh_by_viewport: dict[str, int] = {}
        self.secrets = [value for value in [self.email, self.password] if value]
        self.access_token = ""

    def sanitize(self, value: object) -> str:
        text = str(value)
        for secret in [*self.secrets, self.access_token]:
            if secret:
                text = text.replace(secret, "[REDACTED]")
        text = re.sub(r"Bearer\s+[A-Za-z0-9._~+/=-]+", "Bearer [REDACTED]", text, flags=re.I)
        text = re.sub(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b", "[REDACTED_JWT]", text)
        return text[:1200]

    def has_secret_value(self, text: str) -> bool:
        if any(secret and secret in text for secret in [*self.secrets, self.access_token]):
            return True
        return any(pattern.search(text) for pattern in TOKEN_PATTERNS)

    def finding(self, severity: str, viewport: str, scenario: str, category: str, detail: object) -> None:
        self.findings.append({
            "severity": severity,
            "viewport": viewport,
            "scenario": scenario,
            "category": category,
            "detail": self.sanitize(detail),
        })

    def prepare_fixtures(self) -> None:
        status, login = api_json(
            "POST",
            f"{self.api}/api/v1/auth/login",
            {"email": self.email, "password": self.password},
        )
        if status != 200 or not isinstance(login, dict) or not login.get("access_token"):
            raise RuntimeError(f"fixture login failed HTTP {status}")
        self.access_token = str(login["access_token"])
        common = {"Authorization": f"Bearer {self.access_token}"}
        for workspace_id, marker in [(self.workspace_a, self.marker_a), (self.workspace_b, self.marker_b)]:
            status, response = api_json(
                "POST",
                f"{self.api}/api/v1/leads",
                {"name": marker, "instagram_username": marker.lower()},
                {**common, "X-Workspace-ID": workspace_id},
            )
            if status not in (200, 201) or not isinstance(response, dict) or not response.get("id"):
                raise RuntimeError(f"fixture lead create failed for QA workspace HTTP {status}: {self.sanitize(response)}")
            self.fixture_ids.append((workspace_id, str(response["id"])))

    def cleanup_fixtures(self) -> None:
        if not self.access_token:
            return
        for workspace_id, lead_id in self.fixture_ids:
            status, _ = api_json(
                "DELETE",
                f"{self.api}/api/v1/leads/{lead_id}",
                headers={"Authorization": f"Bearer {self.access_token}", "X-Workspace-ID": workspace_id},
            )
            if status not in (200, 204, 404):
                self.finding("WARN", "global", "Cleanup", "fixture_cleanup", f"Lead cleanup HTTP {status}")

    def wait(self, page) -> None:
        try:
            page.wait_for_load_state("domcontentloaded", timeout=15000)
            page.wait_for_load_state("networkidle", timeout=22000)
        except PlaywrightTimeoutError:
            page.wait_for_timeout(2500)

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
                self.workspace_headers.append({"viewport": viewport, "workspace_id": workspace_id, "url": self.sanitize(request.url)})
            if self.has_secret_value(request.url):
                self.finding("FAIL", viewport, "Global", "secret_leak", "Request URL contained an actual credential/token value")

        def on_response(response) -> None:
            parsed = urlparse(response.url)
            path = parsed.path
            is_api = "/api/" in path
            is_document = response.request.resource_type == "document"
            if (is_api or is_document) and (response.status == 404 or response.status >= 500):
                self.finding("FAIL", viewport, "Global", "core_404_500", f"HTTP {response.status}: {response.url}")
            if is_api or is_document:
                self.network.append({"viewport": viewport, "status": response.status, "url": self.sanitize(response.url)})

        def on_failed(request) -> None:
            if request.resource_type not in ("document", "xhr", "fetch"):
                return
            detail = f"{request.url}: {request.failure}"
            category = "cors_error" if "cors" in detail.lower() else "network_failure"
            self.finding("FAIL", viewport, "Global", category, detail)

        page.on("console", on_console)
        page.on("pageerror", on_page_error)
        page.on("request", on_request)
        page.on("response", on_response)
        page.on("requestfailed", on_failed)

    def open_workspace_menu(self, page, width: int) -> None:
        if width >= 768:
            page.locator(".account-profile-trigger").click(timeout=10000)
        else:
            page.locator(".topbar-action").click(timeout=10000)
        page.wait_for_timeout(500)

    def switch_workspace_ui(self, page, viewport: str, width: int, workspace_name: str, workspace_id: str) -> None:
        self.open_workspace_menu(page, width)
        target = page.get_by_role("button", name=re.compile(re.escape(workspace_name), re.I))
        if target.count() == 0:
            self.finding("FAIL", viewport, "Workspace switch", "workspace_control", f"Workspace option not found: {workspace_name}")
            page.keyboard.press("Escape")
            return
        start = len(self.workspace_headers)
        target.first.click(timeout=10000)
        self.wait(page)
        page.goto(f"{self.frontend}/dashboard", wait_until="domcontentloaded", timeout=30000)
        self.wait(page)
        current = page.evaluate("localStorage.getItem('sellora.current_workspace_id')")
        wrong = [item for item in self.workspace_headers[start:] if item.get("workspace_id") != workspace_id]
        if current != workspace_id:
            self.finding("FAIL", viewport, "Workspace switch", "workspace_state", f"Expected {workspace_id}, got {current}")
        if wrong:
            self.finding("FAIL", viewport, "Workspace switch", "workspace_stale_header", wrong[:3])

    def login(self, page, viewport: str, width: int) -> None:
        page.goto(f"{self.frontend}/login", wait_until="domcontentloaded", timeout=30000)
        self.wait(page)
        page.screenshot(path=str(SHOTS / f"{viewport}-login.png"))
        page.locator('input[type="email"], input[autocomplete="email"]').first.fill(self.email)
        page.locator('input[type="password"], input[autocomplete="current-password"]').first.fill(self.password)
        page.locator('button[type="submit"]').first.click()
        self.wait(page)
        if "/login" in page.url:
            self.finding("FAIL", viewport, "Login", "auth", "Login did not leave /login")
            return
        if not page.evaluate("Boolean(localStorage.getItem('sellora.access_token') && localStorage.getItem('sellora.refresh_token'))"):
            self.finding("FAIL", viewport, "Login", "auth", "Session tokens missing after login")
        self.switch_workspace_ui(page, viewport, width, self.workspace_a_name, self.workspace_a)
        self.results.append({"viewport": viewport, "scenario": "Login", "status": "PASS", "path": "/login"})

    def inspect_route(self, page, viewport: str, scenario: str, path: str) -> None:
        before_failures = len([item for item in self.findings if item["severity"] == "FAIL"])
        page.goto(f"{self.frontend}{path}", wait_until="domcontentloaded", timeout=30000)
        self.wait(page)
        body = page.locator("body").inner_text(timeout=10000)[:12000]
        for pattern in VISIBLE_ERROR_PATTERNS:
            if pattern.search(body):
                self.finding("FAIL", viewport, scenario, "visible_error", f"Visible error matched: {pattern.pattern}")
        if self.has_secret_value(body):
            self.finding("FAIL", viewport, scenario, "secret_leak", "DOM contained an actual credential/token value")
        overflow = bool(page.evaluate("document.documentElement.scrollWidth > window.innerWidth + 2 || document.body.scrollWidth > window.innerWidth + 2"))
        if overflow:
            self.finding("FAIL", viewport, scenario, "responsive_overflow", "Body-level horizontal overflow")
        safe_name = scenario.lower().replace(" ", "-")
        page.screenshot(path=str(SHOTS / f"{viewport}-{safe_name}.png"))
        after_failures = len([item for item in self.findings if item["severity"] == "FAIL"])
        self.results.append({
            "viewport": viewport,
            "scenario": scenario,
            "status": "PASS" if after_failures == before_failures else "FAIL",
            "path": path,
            "overflow": overflow,
            "url": self.sanitize(page.url),
        })

    def verify_workspace_isolation(self, page, viewport: str, width: int) -> None:
        self.switch_workspace_ui(page, viewport, width, self.workspace_a_name, self.workspace_a)
        page.goto(f"{self.frontend}/leads", wait_until="domcontentloaded", timeout=30000)
        self.wait(page)
        body_a = page.locator("body").inner_text()[:15000]
        if self.marker_a not in body_a or self.marker_b in body_a:
            self.finding("FAIL", viewport, "Workspace switch", "workspace_stale_data", "Workspace A marker visibility was incorrect")

        self.switch_workspace_ui(page, viewport, width, self.workspace_b_name, self.workspace_b)
        page.goto(f"{self.frontend}/leads", wait_until="domcontentloaded", timeout=30000)
        self.wait(page)
        body_b = page.locator("body").inner_text()[:15000]
        if self.marker_b not in body_b or self.marker_a in body_b:
            self.finding("FAIL", viewport, "Workspace switch", "workspace_stale_data", "Workspace B marker visibility was incorrect")
        page.screenshot(path=str(SHOTS / f"{viewport}-workspace-b-leads.png"))
        self.results.append({"viewport": viewport, "scenario": "Workspace switch", "status": "PASS", "path": "/leads"})
        self.switch_workspace_ui(page, viewport, width, self.workspace_a_name, self.workspace_a)

    def logout(self, page, viewport: str, width: int) -> None:
        self.open_workspace_menu(page, width)
        target = page.get_by_role("menuitem", name=re.compile(r"Вийти|Logout|Sign out", re.I))
        if target.count() == 0:
            target = page.get_by_text(re.compile(r"Вийти|Logout|Sign out", re.I))
        if target.count() == 0:
            self.finding("FAIL", viewport, "Logout", "logout_control", "Logout control not found")
            return
        target.first.click(timeout=10000)
        self.wait(page)
        tokens_present = page.evaluate("Boolean(localStorage.getItem('sellora.access_token') || localStorage.getItem('sellora.refresh_token'))")
        if tokens_present or "/login" not in page.url:
            self.finding("FAIL", viewport, "Logout", "auth", "Logout did not clear session and return to /login")
        self.results.append({"viewport": viewport, "scenario": "Logout", "status": "PASS" if not tokens_present and "/login" in page.url else "FAIL", "path": "/login"})

    def run_viewport(self, browser, viewport: str, width: int, height: int) -> None:
        context = browser.new_context(viewport={"width": width, "height": height}, is_mobile=width < 768, has_touch=width < 768)
        page = context.new_page()
        self.watch(page, viewport)
        try:
            self.login(page, viewport, width)
            self.verify_workspace_isolation(page, viewport, width)
            for scenario, path in SCENARIOS:
                self.inspect_route(page, viewport, scenario, path)
            if self.refresh_by_viewport.get(viewport, 0) > 3:
                self.finding("FAIL", viewport, "Global", "refresh_token_loop", f"Refresh requests: {self.refresh_by_viewport[viewport]}")
            self.logout(page, viewport, width)
        except Exception as exc:
            self.finding("FAIL", viewport, "Global", "runner_exception", repr(exc))
            try:
                page.screenshot(path=str(SHOTS / f"{viewport}-runner-exception.png"), full_page=True)
            except Exception:
                pass
        finally:
            context.close()

    def write_report(self) -> str:
        fail_count = sum(item["severity"] == "FAIL" for item in self.findings)
        warn_count = sum(item["severity"] == "WARN" for item in self.findings)
        decision = "PASS" if fail_count == 0 else "FAIL"
        report = {
            "decision": decision,
            "frontend_url": self.frontend,
            "fixture": {
                "workspace_a_name": self.workspace_a_name,
                "workspace_b_name": self.workspace_b_name,
                "workspace_markers_created": len(self.fixture_ids),
                "cleanup_attempted": True,
            },
            "viewports": [{"name": name, "width": width, "height": height} for name, width, height in VIEWPORTS],
            "results": self.results,
            "findings": self.findings,
            "summary": {
                "fail_count": fail_count,
                "warn_count": warn_count,
                "refresh_requests": sum(self.refresh_by_viewport.values()),
                "workspace_header_events": len(self.workspace_headers),
                "core_network_sample": self.network[:100],
            },
            "security": {
                "credentials_suppressed": True,
                "tokens_suppressed": True,
                "api_keys_suppressed": True,
            },
        }
        REPORT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        lines = [
            "# Sellora Sprint 8A.1 Browser/Mobile QA",
            "",
            f"Decision: **{decision}**",
            f"Failures: **{fail_count}**",
            f"Warnings: **{warn_count}**",
            f"Refresh requests: **{report['summary']['refresh_requests']}**",
            "",
            "## Matrix",
            "",
            "| Viewport | Scenario | Status | Path |",
            "|---|---|---:|---|",
        ]
        for item in self.results:
            lines.append(f"| {item['viewport']} | {item['scenario']} | {item['status']} | `{item['path']}` |")
        lines.extend(["", "## Findings", ""])
        if not self.findings:
            lines.append("No findings.")
        else:
            lines.extend(["| Severity | Viewport | Scenario | Category | Detail |", "|---|---|---|---|---|"])
            for finding in self.findings:
                detail = finding["detail"].replace("|", "/")
                lines.append(f"| {finding['severity']} | {finding['viewport']} | {finding['scenario']} | {finding['category']} | {detail} |")
        REPORT_MD.write_text("\n".join(lines), encoding="utf-8")
        return decision

    def run(self) -> str:
        OUT.mkdir(parents=True, exist_ok=True)
        SHOTS.mkdir(parents=True, exist_ok=True)
        try:
            self.prepare_fixtures()
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                try:
                    for viewport in VIEWPORTS:
                        self.run_viewport(browser, *viewport)
                finally:
                    browser.close()
        except Exception as exc:
            self.finding("FAIL", "global", "Setup", "runner_exception", repr(exc))
        finally:
            self.cleanup_fixtures()
        return self.write_report()


if __name__ == "__main__":
    required = [
        "STAGING_FRONTEND_URL",
        "STAGING_API_URL",
        "STAGING_OWNER_EMAIL",
        "STAGING_OWNER_PASSWORD",
        "STAGING_TEST_WORKSPACE_ID",
        "STAGING_SECOND_WORKSPACE_ID",
    ]
    missing = [name for name in required if not env(name)]
    if missing:
        print("Missing required browser QA inputs", file=sys.stderr)
        raise SystemExit(2)
    result = BrowserQa().run()
    print(f"Browser/mobile QA decision: {result}")
    raise SystemExit(0 if result == "PASS" else 1)
