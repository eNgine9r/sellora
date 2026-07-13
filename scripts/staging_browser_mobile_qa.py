#!/usr/bin/env python3
"""Browser/mobile QA gate for Sellora staging.

Temporary QA runner. It uses only staging synthetic credentials from GitHub
secrets and writes sanitized artifacts. It does not print passwords, tokens,
Authorization headers, or API keys.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import TimeoutError, sync_playwright

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
    re.compile("Application error", re.I),
    re.compile("Unhandled Runtime Error", re.I),
    re.compile("Something went wrong", re.I),
]

SENSITIVE_PATTERNS = [
    re.compile("Bearer [A-Za-z0-9._-]+", re.I),
    re.compile("access[_-]?token", re.I),
    re.compile("refresh[_-]?token", re.I),
    re.compile("authorization", re.I),
    re.compile("password", re.I),
    re.compile("api[_-]?key", re.I),
    re.compile("sk-[A-Za-z0-9]", re.I),
]


def env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


class QaRun:
    def __init__(self) -> None:
        self.frontend = env("STAGING_FRONTEND_URL").rstrip("/")
        self.email = env("STAGING_OWNER_EMAIL")
        self.password = env("STAGING_OWNER_PASSWORD")
        self.qa_workspace = env("STAGING_TEST_WORKSPACE_ID")
        self.second_workspace = env("STAGING_SECOND_WORKSPACE_ID")
        self.findings: list[dict[str, str]] = []
        self.results: list[dict[str, object]] = []
        self.network: list[dict[str, object]] = []
        self.refresh_count = 0
        self.workspace_headers: list[dict[str, str]] = []
        self.secrets = [v for v in [self.email, self.password, env("STAGING_MANAGER_EMAIL"), env("STAGING_ANALYST_EMAIL")] if v]

    def sanitize(self, value: object) -> str:
        text = str(value)
        for secret in self.secrets:
            text = text.replace(secret, "[REDACTED]")
        text = re.sub("Bearer [A-Za-z0-9._-]+", "Bearer [REDACTED]", text, flags=re.I)
        text = re.sub("(access[_-]?token|refresh[_-]?token)", "[REDACTED_TOKEN_KEY]", text, flags=re.I)
        return text[:1200]

    def finding(self, severity: str, viewport: str, scenario: str, category: str, detail: object) -> None:
        self.findings.append({
            "severity": severity,
            "viewport": viewport,
            "scenario": scenario,
            "category": category,
            "detail": self.sanitize(detail),
        })

    def contains_sensitive_text(self, text: str) -> bool:
        if any(secret and secret in text for secret in self.secrets):
            return True
        clean = self.sanitize(text)
        return any(pattern.search(clean) for pattern in SENSITIVE_PATTERNS)

    def core_url(self, url: str) -> bool:
        path = urlparse(url).path
        if path.startswith("/_next/static") or path.startswith("/_next/image"):
            return False
        if path.endswith("/favicon.ico") or path.endswith("/robots.txt") or path.endswith("/manifest.json"):
            return False
        return url.startswith("http")

    def wait(self, page) -> None:
        try:
            page.wait_for_load_state("domcontentloaded", timeout=15000)
            page.wait_for_load_state("networkidle", timeout=20000)
        except TimeoutError:
            page.wait_for_timeout(2500)

    def watch(self, page, viewport: str) -> None:
        def on_console(msg):
            txt = self.sanitize(msg.text)
            if msg.type == "error":
                self.finding("FAIL", viewport, "Global", "runtime_exception", f"console.error: {txt}")
            if self.contains_sensitive_text(txt):
                self.finding("FAIL", viewport, "Global", "secret_leak", f"console contained sensitive text: {txt}")

        def on_page_error(exc):
            self.finding("FAIL", viewport, "Global", "runtime_exception", repr(exc))

        def on_request(req):
            url = req.url
            if "/auth/refresh" in url:
                self.refresh_count += 1
            headers = req.headers
            wid = headers.get("x-workspace-id") or headers.get("X-Workspace-ID")
            if wid:
                self.workspace_headers.append({"workspace_id": wid, "url": self.sanitize(url)})
            if self.contains_sensitive_text(url):
                self.finding("FAIL", viewport, "Global", "secret_leak", f"request URL contained sensitive text: {url}")

        def on_response(resp):
            url = resp.url
            status = resp.status
            if self.core_url(url) and (status == 404 or status >= 500):
                self.finding("FAIL", viewport, "Global", "core_404_500", f"HTTP {status}: {url}")
            self.network.append({"viewport": viewport, "status": status, "url": self.sanitize(url)})

        def on_failed(req):
            detail = f"{req.url}: {req.failure}"
            category = "cors_error" if "cors" in detail.lower() else "network_failure"
            self.finding("FAIL", viewport, "Global", category, detail)

        page.on("console", on_console)
        page.on("pageerror", on_page_error)
        page.on("request", on_request)
        page.on("response", on_response)
        page.on("requestfailed", on_failed)

    def login(self, page, viewport: str) -> dict:
        page.goto(f"{self.frontend}/login", wait_until="domcontentloaded", timeout=30000)
        self.wait(page)
        page.locator('input[type="email"], input[autocomplete="email"], input[name*="email" i]').first.fill(self.email, timeout=10000)
        page.locator('input[type="password"], input[autocomplete="current-password"], input[name*="password" i]').first.fill(self.password, timeout=10000)
        page.locator('button[type="submit"], button:has-text("Увійти"), button:has-text("Login"), button:has-text("Sign in")').first.click(timeout=10000)
        self.wait(page)
        current_workspace = page.evaluate("localStorage.getItem('sellora.current_workspace_id')")
        user = page.evaluate("JSON.parse(localStorage.getItem('sellora.current_user') || 'null')") or {}
        tokens_present = page.evaluate("Boolean(localStorage.getItem('sellora.access_token') && localStorage.getItem('sellora.refresh_token'))")
        if "/login" in page.url:
            self.finding("FAIL", viewport, "Login", "auth", f"Still on login page: {page.url}")
        if not tokens_present:
            self.finding("FAIL", viewport, "Login", "auth", "Tokens missing after login")
        if self.qa_workspace and current_workspace != self.qa_workspace:
            self.finding("FAIL", viewport, "Login", "workspace", f"Expected QA workspace but got {current_workspace}")
        self.results.append({"viewport": viewport, "scenario": "Login", "path": "/login", "status": "PASS", "url": self.sanitize(page.url), "overflow": False})
        return {"workspace": current_workspace, "user": user}

    def inspect_page(self, page, viewport: str, scenario: str, path: str) -> None:
        page.goto(f"{self.frontend}{path}", wait_until="domcontentloaded", timeout=30000)
        self.wait(page)
        body = page.locator("body").inner_text(timeout=10000)[:6000]
        status = "PASS"
        detail = ""
        for pattern in VISIBLE_ERROR_PATTERNS:
            if pattern.search(body):
                status = "FAIL"
                detail = f"Visible error matched {pattern.pattern}"
                self.finding("FAIL", viewport, scenario, "visible_error", detail)
        if self.contains_sensitive_text(body):
            status = "FAIL"
            detail = "Sensitive text visible in DOM"
            self.finding("FAIL", viewport, scenario, "secret_leak", detail)
        overflow = bool(page.evaluate("document.documentElement.scrollWidth > window.innerWidth + 2 || document.body.scrollWidth > window.innerWidth + 2"))
        screenshot = ""
        if overflow:
            status = "FAIL"
            detail = "Body-level horizontal overflow"
            self.finding("FAIL", viewport, scenario, "responsive_overflow", detail)
            screenshot = str(SHOTS / f"{viewport}-{scenario.lower().replace(' ', '-')}.png")
            page.screenshot(path=screenshot, full_page=True)
        self.results.append({"viewport": viewport, "scenario": scenario, "path": path, "status": status, "url": self.sanitize(page.url), "overflow": overflow, "screenshot": screenshot, "detail": detail})

    def workspace_switch(self, page, viewport: str, state: dict) -> None:
        memberships = state.get("user", {}).get("memberships", [])
        current = state.get("workspace")
        candidate = self.second_workspace or next((str(m.get("workspace_id")) for m in memberships if str(m.get("workspace_id")) != str(current)), "")
        if not candidate:
            self.finding("WARN", viewport, "Workspace switch", "coverage", "Only one workspace membership found; A/B stale-data check could not be exercised")
            self.results.append({"viewport": viewport, "scenario": "Workspace switch", "path": "n/a", "status": "SKIP", "url": self.sanitize(page.url), "overflow": False, "detail": "single workspace membership"})
            return
        start = len(self.workspace_headers)
        page.evaluate("workspaceId => localStorage.setItem('sellora.current_workspace_id', workspaceId)", candidate)
        page.goto(f"{self.frontend}/dashboard", wait_until="domcontentloaded", timeout=30000)
        self.wait(page)
        page.goto(f"{self.frontend}/leads", wait_until="domcontentloaded", timeout=30000)
        self.wait(page)
        wrong = [h for h in self.workspace_headers[start:] if h.get("workspace_id") != candidate]
        if wrong:
            self.finding("FAIL", viewport, "Workspace switch", "workspace_stale_data", wrong[:3])
        self.results.append({"viewport": viewport, "scenario": "Workspace switch", "path": "localStorage+reload", "status": "PASS" if not wrong else "FAIL", "url": self.sanitize(page.url), "overflow": False})
        if current:
            page.evaluate("workspaceId => localStorage.setItem('sellora.current_workspace_id', workspaceId)", current)
            page.goto(f"{self.frontend}/dashboard", wait_until="domcontentloaded", timeout=30000)
            self.wait(page)

    def logout(self, page, viewport: str) -> None:
        clicked = False
        # Try common menu openers first, then logout labels.
        for text in ["Вийти", "Logout", "Sign out"]:
            loc = page.get_by_text(text, exact=False)
            if loc.count() > 0:
                loc.first.click(timeout=4000)
                clicked = True
                break
        if not clicked:
            for button in page.locator("button").all()[:20]:
                try:
                    button.click(timeout=1000)
                    page.wait_for_timeout(300)
                    for text in ["Вийти", "Logout", "Sign out"]:
                        loc = page.get_by_text(text, exact=False)
                        if loc.count() > 0:
                            loc.first.click(timeout=4000)
                            clicked = True
                            break
                    if clicked:
                        break
                except Exception:
                    continue
        if not clicked:
            self.finding("WARN", viewport, "Logout", "coverage", "Logout control not found by accessible text")
            self.results.append({"viewport": viewport, "scenario": "Logout", "path": "UI", "status": "SKIP", "url": self.sanitize(page.url), "overflow": False})
            return
        self.wait(page)
        access_present = page.evaluate("Boolean(localStorage.getItem('sellora.access_token'))")
        ok = (not access_present) and ("/login" in page.url)
        if not ok:
            self.finding("FAIL", viewport, "Logout", "auth", f"Token still present or not redirected: {page.url}")
        self.results.append({"viewport": viewport, "scenario": "Logout", "path": "UI", "status": "PASS" if ok else "FAIL", "url": self.sanitize(page.url), "overflow": False})

    def run_viewport(self, browser, name: str, width: int, height: int) -> None:
        context = browser.new_context(viewport={"width": width, "height": height}, is_mobile=width < 768, has_touch=width < 768)
        page = context.new_page()
        self.watch(page, name)
        try:
            state = self.login(page, name)
            self.workspace_switch(page, name, state)
            for scenario, path in SCENARIOS:
                self.inspect_page(page, name, scenario, path)
            if self.refresh_count > 20:
                self.finding("FAIL", name, "Global", "refresh_token_loop", f"Too many refresh requests: {self.refresh_count}")
            self.logout(page, name)
        except Exception as exc:
            self.finding("FAIL", name, "Global", "runner_exception", repr(exc))
            try:
                page.screenshot(path=str(SHOTS / f"{name}-runner-exception.png"), full_page=True)
            except Exception:
                pass
        finally:
            context.close()

    def report(self) -> str:
        fail_count = sum(1 for f in self.findings if f["severity"] == "FAIL")
        warn_count = sum(1 for f in self.findings if f["severity"] == "WARN")
        decision = "PASS" if fail_count == 0 else "FAIL"
        data = {
            "decision": decision,
            "frontend_url": self.frontend,
            "viewports": [{"name": n, "width": w, "height": h} for n, w, h in VIEWPORTS],
            "results": self.results,
            "findings": self.findings,
            "summary": {"fail_count": fail_count, "warn_count": warn_count, "refresh_requests": self.refresh_count, "workspace_header_events": len(self.workspace_headers), "network_sample": self.network[:80]},
        }
        REPORT_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        lines = ["# Sellora Sprint 8A.1 Browser/Mobile QA", "", f"Decision: **{decision}**", f"Failures: **{fail_count}**", f"Warnings: **{warn_count}**", f"Refresh requests: **{self.refresh_count}**", "", "## Matrix", "", "| Viewport | Scenario | Status | Overflow | URL |", "|---|---|---:|---:|---|"]
        for r in self.results:
            lines.append(f"| {r['viewport']} | {r['scenario']} | {r['status']} | {r.get('overflow', False)} | `{r['url']}` |")
        lines += ["", "## Findings", ""]
        if self.findings:
            lines.append("| Severity | Viewport | Scenario | Category | Detail |")
            lines.append("|---|---|---|---|---|")
            for f in self.findings:
                detail = str(f["detail"]).replace("|", "/")
                lines.append(f"| {f['severity']} | {f['viewport']} | {f['scenario']} | {f['category']} | {detail} |")
        else:
            lines.append("No findings.")
        REPORT_MD.write_text("\n".join(lines), encoding="utf-8")
        return decision

    def run(self) -> str:
        OUT.mkdir(parents=True, exist_ok=True)
        SHOTS.mkdir(parents=True, exist_ok=True)
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                for item in VIEWPORTS:
                    self.run_viewport(browser, *item)
            finally:
                browser.close()
        return self.report()


if __name__ == "__main__":
    missing = [k for k in ["STAGING_FRONTEND_URL", "STAGING_OWNER_EMAIL", "STAGING_OWNER_PASSWORD", "STAGING_TEST_WORKSPACE_ID"] if not env(k)]
    if missing:
        print("Missing env vars: " + ", ".join(missing), file=sys.stderr)
        raise SystemExit(2)
    decision = QaRun().run()
    print("Browser/mobile QA decision:", decision)
    raise SystemExit(0 if decision == "PASS" else 1)
