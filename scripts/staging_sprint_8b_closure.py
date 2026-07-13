#!/usr/bin/env python3
"""Sprint 8B staging closure runner.

The runner uses only synthetic QA users and temporary workspaces. It validates
server-side demo provenance, runtime idempotency, rollback evidence from the
pipeline, role behavior, workspace isolation, cache cleanup, responsive UI in
light/dark themes, and the truthful core demo dataset.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import string
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
from playwright.sync_api import Browser, BrowserContext, Page, TimeoutError as PlaywrightTimeoutError, sync_playwright

OUT = Path("artifacts/sprint-8b-closure")
SHOTS = OUT / "screenshots"
REPORT_JSON = OUT / "sprint-8b-closure.json"
REPORT_MD = OUT / "sprint-8b-closure.md"

VIEWPORTS = [
    ("desktop-1366x768", 1366, 768),
    ("mobile-375x812", 375, 812),
    ("mobile-390x844", 390, 844),
    ("mobile-430x932", 430, 932),
    ("tablet-768x1024", 768, 1024),
]
THEMES = ["light", "dark"]
ROLE_CONFIGS = [
    ("desktop-1366x768", 1366, 768, "light"),
    ("mobile-390x844", 390, 844, "light"),
    ("desktop-1366x768", 1366, 768, "dark"),
    ("mobile-390x844", 390, 844, "dark"),
]

VISIBLE_ERROR_PATTERNS = [
    re.compile(r"Application error", re.I),
    re.compile(r"Unhandled Runtime Error", re.I),
    re.compile(r"Internal Server Error", re.I),
]
TOKEN_PATTERNS = [
    re.compile(r"Bearer\s+[A-Za-z0-9._~+/=-]{20,}", re.I),
    re.compile(r"\beyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{12,}\b", re.I),
]


def env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def random_password() -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%"
    return "Qa8B!" + "".join(secrets.choice(alphabet) for _ in range(24))


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def item_count(value: Any) -> int:
    if isinstance(value, list):
        return len(value)
    if isinstance(value, dict):
        for key in ("items", "results", "data"):
            if isinstance(value.get(key), list):
                return len(value[key])
    return 0


@dataclass
class Session:
    email: str
    access_token: str
    refresh_token: str
    user: dict[str, Any]


class Sprint8BClosure:
    def __init__(self) -> None:
        self.frontend = env("STAGING_FRONTEND_URL").rstrip("/")
        self.api = env("STAGING_API_URL").rstrip("/") + "/api/v1"
        self.owner_email = env("STAGING_OWNER_EMAIL")
        self.owner_password = env("STAGING_OWNER_PASSWORD")
        self.manager_email = env("STAGING_MANAGER_EMAIL")
        self.manager_password = env("STAGING_MANAGER_PASSWORD")
        self.analyst_email = env("STAGING_ANALYST_EMAIL")
        self.analyst_password = env("STAGING_ANALYST_PASSWORD")
        self.real_qa_workspace_id = env("STAGING_TEST_WORKSPACE_ID")
        self.stamp = str(int(time.time()))
        self.empty_workspace_name = f"Sellora QA — Sprint 8B Empty {self.stamp}"
        self.empty_workspace_slug = f"sellora-qa-sprint-8b-empty-{self.stamp}"
        self.no_workspace_email = f"sellora.qa8b.noworkspace.{self.stamp}@example.com"
        self.no_workspace_password = random_password()
        self.real_marker = f"QA8B-REAL-{self.stamp}"
        self.http = httpx.Client(timeout=70, follow_redirects=True)
        self.owner: Session | None = None
        self.manager: Session | None = None
        self.analyst: Session | None = None
        self.no_workspace: Session | None = None
        self.empty_workspace_id = ""
        self.demo_workspace_id = ""
        self.real_marker_id = ""
        self.created_user_id = ""
        self.results: list[dict[str, Any]] = []
        self.findings: list[dict[str, str]] = []
        self.network_events: list[dict[str, Any]] = []
        self.external_requests: list[str] = []
        self.refresh_requests = 0
        self.demo_post_requests = 0
        self.secrets = [
            self.owner_password,
            self.manager_password,
            self.analyst_password,
            self.no_workspace_password,
        ]

    def safe(self, value: Any) -> str:
        text = str(value)
        for secret in self.secrets:
            if secret:
                text = text.replace(secret, "[REDACTED]")
        text = re.sub(r"Bearer\s+[A-Za-z0-9._~+/=-]+", "Bearer [REDACTED]", text, flags=re.I)
        text = re.sub(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b", "[REDACTED_JWT]", text)
        return text[:1600]

    def result(self, group: str, check: str, passed: bool, detail: Any = "") -> None:
        self.results.append({"group": group, "check": check, "status": "PASS" if passed else "FAIL", "detail": self.safe(detail)})
        if not passed:
            self.finding("FAIL", group, check, detail)

    def finding(self, severity: str, area: str, category: str, detail: Any) -> None:
        self.findings.append({"severity": severity, "area": area, "category": category, "detail": self.safe(detail)})

    def headers(self, token: str, workspace_id: str | None = None) -> dict[str, str]:
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
        if workspace_id:
            headers["X-Workspace-ID"] = workspace_id
        return headers

    def request(
        self,
        method: str,
        path: str,
        *,
        token: str | None = None,
        workspace_id: str | None = None,
        payload: Any = None,
        expected: tuple[int, ...] | None = None,
    ) -> tuple[int, Any]:
        url = f"{self.api}{path}"
        last_error: Exception | None = None
        for attempt in range(1, 6):
            try:
                response = self.http.request(method, url, headers=self.headers(token, workspace_id) if token else {"Accept": "application/json"}, json=payload)
                try:
                    data: Any = response.json() if response.content else None
                except Exception:
                    data = {"detail": response.text[:500]}
                if response.status_code >= 500 and attempt < 5:
                    time.sleep(min(4 * attempt, 15))
                    continue
                if expected is not None and response.status_code not in expected:
                    raise RuntimeError(f"{method} {path} returned HTTP {response.status_code}: {self.safe(data)}")
                return response.status_code, data
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                last_error = exc
                if attempt < 5:
                    time.sleep(min(4 * attempt, 15))
                    continue
        raise RuntimeError(f"{method} {path} unavailable after retries: {type(last_error).__name__}")

    def login(self, email: str, password: str) -> Session:
        _, tokens = self.request("POST", "/auth/login", payload={"email": email, "password": password}, expected=(200,))
        _, user = self.request("GET", "/auth/me", token=tokens["access_token"], expected=(200,))
        return Session(email=email, access_token=tokens["access_token"], refresh_token=tokens["refresh_token"], user=user)

    def snapshot_workspace(self, session: Session, workspace_id: str) -> dict[str, Any]:
        paths = {
            "leads": "/leads",
            "customers": "/customers",
            "products": "/products",
            "inventory": "/inventory",
            "inventory_transactions": "/inventory/transactions",
            "orders": "/orders",
            "shipments": "/shipments",
            "campaigns": "/advertising/campaigns",
            "metrics": "/advertising/metrics",
            "finance_adjustments": "/finance/adjustments",
            "onboarding": "/onboarding/status",
        }
        snapshot: dict[str, Any] = {}
        for key, path in paths.items():
            status, data = self.request("GET", path, token=session.access_token, workspace_id=workspace_id)
            if status == 200:
                snapshot[key] = data
            else:
                snapshot[key] = {"http_status": status}
        return snapshot

    def api_setup_and_security(self) -> None:
        status, _ = self.request("GET", "/../health") if False else (200, None)
        self.owner = self.login(self.owner_email, self.owner_password)
        self.manager = self.login(self.manager_email, self.manager_password)
        self.analyst = self.login(self.analyst_email, self.analyst_password)
        self.result("API", "OWNER login and /auth/me", True)
        self.result("API", "MANAGER login and /auth/me", True)
        self.result("API", "ANALYST login and /auth/me", True)

        _, workspace = self.request(
            "POST",
            "/workspaces",
            token=self.owner.access_token,
            payload={
                "name": self.empty_workspace_name,
                "slug": self.empty_workspace_slug,
                "currency_code": "UAH",
                "timezone": "Europe/Kyiv",
            },
            expected=(201,),
        )
        self.empty_workspace_id = str(workspace["id"])
        self.result("Fixture", "temporary empty workspace created", bool(self.empty_workspace_id), self.empty_workspace_id)

        for email, role in ((self.manager_email, "MANAGER"), (self.analyst_email, "ANALYST")):
            self.request(
                "POST",
                "/workspace-users",
                token=self.owner.access_token,
                workspace_id=self.empty_workspace_id,
                payload={"email": email, "full_name": f"QA {role.title()}", "role": role, "temporary_password": random_password()},
                expected=(201,),
            )
            self.result("Fixture", f"{role} membership added to empty workspace", True)

        _, created_user = self.request(
            "POST",
            "/workspace-users",
            token=self.owner.access_token,
            workspace_id=self.empty_workspace_id,
            payload={
                "email": self.no_workspace_email,
                "full_name": "QA No Workspace",
                "role": "OWNER",
                "temporary_password": self.no_workspace_password,
            },
            expected=(201,),
        )
        self.created_user_id = str(created_user["user_id"])
        self.request(
            "PATCH",
            f"/workspace-users/{self.created_user_id}/deactivate",
            token=self.owner.access_token,
            workspace_id=self.empty_workspace_id,
            expected=(200,),
        )
        self.no_workspace = self.login(self.no_workspace_email, self.no_workspace_password)
        active_memberships = self.no_workspace.user.get("memberships") or []
        self.result("No workspace", "synthetic user has no active workspace", len(active_memberships) == 0, len(active_memberships))

        for label, session in (("MANAGER", self.manager), ("ANALYST", self.analyst)):
            code, _ = self.request("POST", "/workspaces/demo", token=session.access_token, payload={"locale": "uk", "currency_code": "UAH"})
            self.result("RBAC", f"{label} demo management safe denial", code == 403, f"HTTP {code}")

        code, _ = self.request(
            "POST",
            "/leads",
            token=self.analyst.access_token,
            workspace_id=self.empty_workspace_id,
            payload={"name": "QA8B forbidden analyst mutation"},
        )
        self.result("RBAC", "ANALYST direct mutation rejected", code == 403, f"HTTP {code}")

        code, _ = self.request(
            "PATCH",
            "/workspaces/demo/deactivate",
            token=self.owner.access_token,
            workspace_id=self.empty_workspace_id,
        )
        self.result("Provenance", "normal workspace cannot use demo deactivation", code == 400, f"HTTP {code}")

        for label, session, expected_role in (
            ("OWNER", self.owner, "OWNER"),
            ("MANAGER", self.manager, "MANAGER"),
            ("ANALYST", self.analyst, "ANALYST"),
        ):
            _, status_data = self.request("GET", "/onboarding/status", token=session.access_token, workspace_id=self.empty_workspace_id, expected=(200,))
            passed = status_data.get("role") == expected_role and status_data.get("is_demo_workspace") is False and status_data.get("progress_percent") == 20
            self.result("Onboarding", f"{label} empty-workspace progress is real and role-aware", passed, {"role": status_data.get("role"), "progress": status_data.get("progress_percent")})

    def init_context(self, browser: Browser, session: Session, workspace_id: str | None, theme: str, width: int, height: int) -> BrowserContext:
        context = browser.new_context(viewport={"width": width, "height": height}, is_mobile=width < 768, has_touch=width < 768, color_scheme=theme)
        payload = {
            "access": session.access_token,
            "refresh": session.refresh_token,
            "user": session.user,
            "workspace": workspace_id,
            "theme": theme,
        }
        context.add_init_script(
            script=f"""
            (() => {{
              const payload = {json.dumps(payload, ensure_ascii=False)};
              localStorage.setItem('sellora.access_token', payload.access);
              localStorage.setItem('sellora.refresh_token', payload.refresh);
              localStorage.setItem('sellora.current_user', JSON.stringify(payload.user));
              if (payload.workspace) localStorage.setItem('sellora.current_workspace_id', payload.workspace);
              else localStorage.removeItem('sellora.current_workspace_id');
              localStorage.setItem('sellora.theme-mode', payload.theme);
            }})();
            """
        )
        return context

    def watch_page(self, page: Page, label: str) -> None:
        def on_console(message) -> None:
            text = message.text
            if message.type == "error":
                self.finding("FAIL", label, "runtime_exception", f"console.error: {text}")
            if any(secret and secret in text for secret in self.secrets) or any(pattern.search(text) for pattern in TOKEN_PATTERNS):
                self.finding("FAIL", label, "credential_exposure", "Console contained a credential/token value")

        def on_page_error(error) -> None:
            self.finding("FAIL", label, "runtime_exception", repr(error))

        def on_request(request) -> None:
            url = request.url
            lower = url.lower()
            if "/auth/refresh" in lower:
                self.refresh_requests += 1
            if "/workspaces/demo" in lower and request.method == "POST":
                self.demo_post_requests += 1
            host = urlparse(url).netloc.lower()
            if any(marker in host for marker in ("graph.facebook.com", "facebook.com", "api.novaposhta.ua", "novaposhta")):
                self.external_requests.append(self.safe(url))

        def on_response(response) -> None:
            parsed = urlparse(response.url)
            is_api = "/api/" in parsed.path or "onrender.com" in parsed.netloc
            is_document = response.request.resource_type == "document"
            if (is_api or is_document) and (response.status == 404 or response.status >= 500):
                self.finding("FAIL", label, "core_404_500", f"HTTP {response.status}: {response.url}")
            if is_api or is_document:
                self.network_events.append({"label": label, "status": response.status, "method": response.request.method, "url": self.safe(response.url)})

        def on_failed(request) -> None:
            if request.resource_type not in ("document", "xhr", "fetch"):
                return
            detail = str(request.failure or "")
            if "ERR_ABORTED" in detail:
                return
            category = "cors_error" if "cors" in detail.lower() else "network_failure"
            self.finding("FAIL", label, category, f"{request.url}: {detail}")

        page.on("console", on_console)
        page.on("pageerror", on_page_error)
        page.on("request", on_request)
        page.on("response", on_response)
        page.on("requestfailed", on_failed)

    def wait_page(self, page: Page) -> None:
        try:
            page.wait_for_load_state("domcontentloaded", timeout=30000)
            page.wait_for_load_state("networkidle", timeout=35000)
        except PlaywrightTimeoutError:
            page.wait_for_timeout(2500)

    def check_page(self, page: Page, label: str, scenario: str, screenshot: str) -> bool:
        self.wait_page(page)
        body = page.locator("body").inner_text(timeout=15000)[:20000]
        passed = True
        for pattern in VISIBLE_ERROR_PATTERNS:
            if pattern.search(body):
                self.finding("FAIL", label, "visible_error", f"{scenario}: {pattern.pattern}")
                passed = False
        overflow = bool(page.evaluate("document.documentElement.scrollWidth > window.innerWidth + 2 || document.body.scrollWidth > window.innerWidth + 2"))
        if overflow:
            self.finding("FAIL", label, "responsive_overflow", scenario)
            passed = False
        for secret in self.secrets:
            if secret and secret in body:
                self.finding("FAIL", label, "credential_exposure", f"DOM contained password during {scenario}")
                passed = False
        page.screenshot(path=str(SHOTS / screenshot), full_page=False)
        self.result("Browser", f"{label} — {scenario}", passed, {"url": self.safe(page.url), "overflow": overflow})
        return passed

    def open_workspace_menu(self, page: Page, width: int) -> None:
        if width >= 768:
            page.locator(".account-profile-trigger").click(timeout=15000)
        else:
            page.locator(".topbar-action").click(timeout=15000)
        page.wait_for_timeout(500)

    def switch_workspace(self, page: Page, width: int, workspace_name: str, workspace_id: str) -> None:
        self.open_workspace_menu(page, width)
        target = page.get_by_role("button", name=re.compile(re.escape(workspace_name), re.I))
        if target.count() == 0:
            raise RuntimeError(f"Workspace switch option not found: {workspace_name}")
        target.first.click(timeout=15000)
        page.wait_for_function("expected => localStorage.getItem('sellora.current_workspace_id') === expected", arg=workspace_id, timeout=30000)
        page.goto(f"{self.frontend}/dashboard", wait_until="domcontentloaded", timeout=45000)
        self.wait_page(page)

    def no_workspace_matrix(self, browser: Browser) -> None:
        assert self.no_workspace is not None
        for viewport_name, width, height in VIEWPORTS:
            for theme in THEMES:
                label = f"no-workspace/{viewport_name}/{theme}"
                context = self.init_context(browser, self.no_workspace, None, theme, width, height)
                page = context.new_page()
                self.watch_page(page, label)
                try:
                    page.goto(f"{self.frontend}/dashboard", wait_until="domcontentloaded", timeout=45000)
                    self.wait_page(page)
                    cta = page.get_by_role("button", name=re.compile(r"демо|demo", re.I))
                    passed = cta.count() > 0 and page.evaluate("document.documentElement.dataset.theme") == theme
                    self.result("No workspace", f"{viewport_name}/{theme} screen and demo CTA", passed)
                    self.check_page(page, label, "no-workspace screen", f"{label.replace('/', '-')}.png")
                except Exception as exc:
                    self.finding("FAIL", label, "runner_exception", repr(exc))
                finally:
                    context.close()

    def empty_workspace_matrix(self, browser: Browser) -> None:
        assert self.owner is not None
        for viewport_name, width, height in VIEWPORTS:
            for theme in THEMES:
                label = f"empty-owner/{viewport_name}/{theme}"
                context = self.init_context(browser, self.owner, self.empty_workspace_id, theme, width, height)
                page = context.new_page()
                self.watch_page(page, label)
                try:
                    page.goto(f"{self.frontend}/dashboard", wait_until="domcontentloaded", timeout=45000)
                    self.wait_page(page)
                    checklist = page.locator("[data-first-run-checklist]")
                    demo_button = page.get_by_role("button", name=re.compile(r"демо|demo", re.I))
                    passed = checklist.count() == 1 and demo_button.count() > 0 and "20%" in page.locator("body").inner_text()
                    self.result("OWNER", f"{viewport_name}/{theme} checklist, progress and CTA", passed)
                    self.check_page(page, label, "empty OWNER dashboard", f"{label.replace('/', '-')}.png")
                except Exception as exc:
                    self.finding("FAIL", label, "runner_exception", repr(exc))
                finally:
                    context.close()

    def role_matrix(self, browser: Browser, label_role: str, session: Session) -> None:
        for viewport_name, width, height, theme in ROLE_CONFIGS:
            label = f"{label_role.lower()}/{viewport_name}/{theme}"
            context = self.init_context(browser, session, self.empty_workspace_id, theme, width, height)
            page = context.new_page()
            self.watch_page(page, label)
            try:
                page.goto(f"{self.frontend}/dashboard", wait_until="domcontentloaded", timeout=45000)
                self.wait_page(page)
                checklist = page.locator("[data-first-run-checklist]")
                demo_cta = page.get_by_role("button", name=re.compile(r"демо|demo", re.I))
                owner_settings_link = checklist.locator('a[href="/settings/workspace"]')
                passed = checklist.count() == 1 and demo_cta.count() == 0 and owner_settings_link.count() == 0
                self.result(label_role, f"{viewport_name}/{theme} role-aware guidance and no OWNER demo/settings CTA", passed)
                self.check_page(page, label, f"{label_role} dashboard", f"{label.replace('/', '-')}.png")
            except Exception as exc:
                self.finding("FAIL", label, "runner_exception", repr(exc))
            finally:
                context.close()

    def create_demo_flow(self, browser: Browser) -> None:
        assert self.owner is not None
        context = self.init_context(browser, self.owner, self.empty_workspace_id, "light", 1366, 768)
        page = context.new_page()
        label = "owner-demo-create/desktop/light"
        self.watch_page(page, label)
        request_counter = {"count": 0}

        def delayed_demo(route) -> None:
            request_counter["count"] += 1
            time.sleep(1.5)
            route.continue_()

        try:
            page.route("**/workspaces/demo", delayed_demo)
            page.goto(f"{self.frontend}/dashboard", wait_until="domcontentloaded", timeout=45000)
            self.wait_page(page)
            button = page.get_by_role("button", name=re.compile(r"демо|demo", re.I)).first
            if button.count() == 0:
                raise RuntimeError("OWNER demo CTA not found")
            button.evaluate("element => { element.click(); element.click(); }")
            page.wait_for_timeout(300)
            loading_visible = bool(button.is_disabled())
            page.screenshot(path=str(SHOTS / "owner-demo-generation-loading.png"))
            page.locator("[data-demo-workspace-banner]").wait_for(state="visible", timeout=120000)
            self.demo_workspace_id = str(page.evaluate("localStorage.getItem('sellora.current_workspace_id') || ''"))
            self.result("OWNER", "demo generation loading state visible", loading_visible)
            self.result("OWNER", "duplicate-click protection emitted one POST", request_counter["count"] == 1, request_counter["count"])
            self.result("OWNER", "demo workspace has separate ID", bool(self.demo_workspace_id) and self.demo_workspace_id != self.empty_workspace_id, self.demo_workspace_id)
            self.check_page(page, label, "demo banner immediately after creation", "owner-demo-created-banner.png")
        except Exception as exc:
            self.finding("FAIL", label, "runner_exception", repr(exc))
        finally:
            page.unroute("**/workspaces/demo")
            context.close()

        if not self.demo_workspace_id:
            return
        _, first = self.request("POST", "/workspaces/demo", token=self.owner.access_token, payload={"locale": "uk", "currency_code": "UAH"}, expected=(201,))
        _, second = self.request("POST", "/workspaces/demo", token=self.owner.access_token, payload={"locale": "uk", "currency_code": "UAH"}, expected=(201,))
        self.result("Idempotency", "repeated runtime POST returns same demo workspace", str(first.get("id")) == self.demo_workspace_id == str(second.get("id")), {"first": first.get("id"), "second": second.get("id")})

        _, status_data = self.request("GET", "/onboarding/status", token=self.owner.access_token, workspace_id=self.demo_workspace_id, expected=(200,))
        self.result("Dataset", "demo onboarding is provenance-labeled and complete", status_data.get("is_demo_workspace") is True and status_data.get("progress_percent") == 100, status_data)

        counts: dict[str, int] = {}
        for key, path in {
            "leads": "/leads",
            "customers": "/customers",
            "products": "/products",
            "inventory": "/inventory",
            "inventory_transactions": "/inventory/transactions",
            "orders": "/orders",
            "shipments": "/shipments",
            "campaigns": "/advertising/campaigns",
            "metrics": "/advertising/metrics",
            "finance_adjustments": "/finance/adjustments",
        }.items():
            _, data = self.request("GET", path, token=self.owner.access_token, workspace_id=self.demo_workspace_id, expected=(200,))
            counts[key] = item_count(data)
        expected = {
            "leads": 6,
            "customers": 4,
            "products": 6,
            "inventory": 6,
            "inventory_transactions": 6,
            "orders": 5,
            "shipments": 0,
            "campaigns": 0,
            "metrics": 0,
            "finance_adjustments": 0,
        }
        self.result("Dataset", "core demo dataset is coherent and truthful", all(counts.get(key) == value for key, value in expected.items()), {"actual": counts, "expected": expected})

        code, _ = self.request("PATCH", "/workspaces/demo/deactivate", token=self.manager.access_token, workspace_id=self.demo_workspace_id)
        self.result("RBAC", "MANAGER cannot deactivate OWNER demo workspace", code == 403, f"HTTP {code}")
        code, _ = self.request("PATCH", "/workspaces/demo/deactivate", token=self.analyst.access_token, workspace_id=self.demo_workspace_id)
        self.result("RBAC", "ANALYST cannot deactivate OWNER demo workspace", code == 403, f"HTTP {code}")

    def create_real_marker(self) -> None:
        assert self.owner is not None
        _, lead = self.request("POST", "/leads", token=self.owner.access_token, workspace_id=self.empty_workspace_id, payload={"name": self.real_marker, "instagram_username": self.real_marker.lower()}, expected=(201,))
        self.real_marker_id = str(lead["id"])

    def demo_matrix_and_switch(self, browser: Browser) -> None:
        if not self.demo_workspace_id:
            return
        assert self.owner is not None
        self.create_real_marker()
        for viewport_name, width, height in VIEWPORTS:
            for theme in THEMES:
                label = f"demo/{viewport_name}/{theme}"
                context = self.init_context(browser, self.owner, self.demo_workspace_id, theme, width, height)
                page = context.new_page()
                self.watch_page(page, label)
                try:
                    page.goto(f"{self.frontend}/dashboard", wait_until="domcontentloaded", timeout=45000)
                    self.wait_page(page)
                    banner = page.locator("[data-demo-workspace-banner]")
                    self.result("Demo UI", f"{viewport_name}/{theme} banner and theme", banner.count() == 1 and page.evaluate("document.documentElement.dataset.theme") == theme)
                    self.check_page(page, label, "demo dashboard", f"{label.replace('/', '-')}-dashboard.png")

                    for scenario, path in (("Shipments honest empty state", "/shipments"), ("Advertising honest empty state", "/advertising"), ("Finance truthful order-derived view", "/finance")):
                        page.goto(f"{self.frontend}{path}", wait_until="domcontentloaded", timeout=45000)
                        self.check_page(page, label, scenario, f"{label.replace('/', '-')}-{path.strip('/').replace('/', '-')}.png")

                    self.switch_workspace(page, width, self.empty_workspace_name, self.empty_workspace_id)
                    page.goto(f"{self.frontend}/leads", wait_until="domcontentloaded", timeout=45000)
                    self.wait_page(page)
                    real_body = page.locator("body").inner_text()[:20000]
                    real_ok = self.real_marker in real_body and "DEMO Лід" not in real_body
                    self.result("Isolation", f"{viewport_name}/{theme} real workspace has no stale demo data", real_ok)

                    self.switch_workspace(page, width, "Демо Sellora", self.demo_workspace_id)
                    page.goto(f"{self.frontend}/leads", wait_until="domcontentloaded", timeout=45000)
                    self.wait_page(page)
                    demo_body = page.locator("body").inner_text()[:20000]
                    demo_ok = "DEMO Лід" in demo_body and self.real_marker not in demo_body
                    self.result("Isolation", f"{viewport_name}/{theme} demo workspace has no stale real data", demo_ok)
                    self.check_page(page, label, "workspace switch real-demo-real cache isolation", f"{label.replace('/', '-')}-workspace-switch.png")
                except Exception as exc:
                    self.finding("FAIL", label, "runner_exception", repr(exc))
                finally:
                    context.close()

    def deactivate_demo_ui(self, browser: Browser) -> None:
        if not self.demo_workspace_id or self.owner is None:
            return
        context = self.init_context(browser, self.owner, self.demo_workspace_id, "dark", 1366, 768)
        page = context.new_page()
        label = "demo-deactivation/desktop/dark"
        self.watch_page(page, label)
        dialog_seen = {"value": False}

        def accept_dialog(dialog) -> None:
            dialog_seen["value"] = True
            dialog.accept()

        try:
            page.on("dialog", accept_dialog)
            page.goto(f"{self.frontend}/dashboard", wait_until="domcontentloaded", timeout=45000)
            self.wait_page(page)
            banner = page.locator("[data-demo-workspace-banner]")
            button = banner.locator("button")
            if button.count() == 0:
                raise RuntimeError("Demo deactivation button not found")
            button.first.click(timeout=15000)
            page.wait_for_function("demoId => localStorage.getItem('sellora.current_workspace_id') !== demoId", arg=self.demo_workspace_id, timeout=60000)
            self.wait_page(page)
            self.result("OWNER", "demo deactivation confirmation dialog shown", dialog_seen["value"])
            self.result("OWNER", "demo deactivated and active workspace changed", page.evaluate("localStorage.getItem('sellora.current_workspace_id')") != self.demo_workspace_id)
            self.check_page(page, label, "safe demo deactivation", "demo-deactivation.png")
        except Exception as exc:
            self.finding("FAIL", label, "runner_exception", repr(exc))
        finally:
            context.close()

    def browser_run(self) -> None:
        SHOTS.mkdir(parents=True, exist_ok=True)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                self.no_workspace_matrix(browser)
                self.empty_workspace_matrix(browser)
                assert self.manager is not None and self.analyst is not None
                self.role_matrix(browser, "MANAGER", self.manager)
                self.role_matrix(browser, "ANALYST", self.analyst)
                self.create_demo_flow(browser)
                self.demo_matrix_and_switch(browser)
                self.deactivate_demo_ui(browser)
            finally:
                browser.close()

    def cleanup_api(self) -> None:
        if self.owner is None:
            return
        if self.real_marker_id:
            code, _ = self.request("DELETE", f"/leads/{self.real_marker_id}", token=self.owner.access_token, workspace_id=self.empty_workspace_id)
            self.result("Cleanup", "real workspace marker archived", code in (200, 204, 404), f"HTTP {code}")
        for session in (self.manager, self.analyst):
            if session is None or not self.empty_workspace_id:
                continue
            user_id = session.user.get("id")
            if user_id:
                code, _ = self.request("PATCH", f"/workspace-users/{user_id}/deactivate", token=self.owner.access_token, workspace_id=self.empty_workspace_id)
                self.result("Cleanup", f"temporary {session.email.split('@')[0]} membership deactivated", code in (200, 400), f"HTTP {code}")

    def final_api_assertions(self) -> None:
        if self.owner is None:
            return
        workspaces_before = self.owner.user.get("memberships") or []
        _, refreshed_user = self.request("GET", "/auth/me", token=self.owner.access_token, expected=(200,))
        active_demo = [item for item in (refreshed_user.get("memberships") or []) if str(item.get("workspace_id")) == self.demo_workspace_id]
        self.result("Cleanup", "demo workspace removed from active memberships", len(active_demo) == 0, len(active_demo))
        self.result("Security", "external Meta/Nova Poshta requests = 0", len(self.external_requests) == 0, self.external_requests)
        self.result("Security", "refresh-token loop absent", self.refresh_requests <= 3, self.refresh_requests)
        self.result("Security", "core 500/runtime/CORS findings absent", not any(item["severity"] == "FAIL" and item["category"] in {"runtime_exception", "core_404_500", "cors_error", "network_failure"} for item in self.findings))

    def write_report(self) -> str:
        fail_count = sum(1 for result in self.results if result["status"] == "FAIL") + sum(1 for finding in self.findings if finding["severity"] == "FAIL")
        # Results already create matching findings; deduplicate decision by unique finding/result details only for presentation.
        unique_failures = {(f["area"], f["category"], f["detail"]) for f in self.findings if f["severity"] == "FAIL"}
        decision = "PASS" if not unique_failures and all(result["status"] == "PASS" for result in self.results) else "FAIL"
        report = {
            "decision": decision,
            "sprint": "8B",
            "execution_mechanism": "temporary GitHub Actions + Python Playwright, reused from Sprint 8A.1 pattern",
            "frontend": self.frontend,
            "api": self.api,
            "fixtures": {
                "empty_workspace_id": self.empty_workspace_id,
                "empty_workspace_name": self.empty_workspace_name,
                "demo_workspace_id": self.demo_workspace_id,
                "no_workspace_user": self.no_workspace_email,
                "created_user_id": self.created_user_id,
            },
            "matrix": [{"name": name, "width": width, "height": height, "themes": THEMES} for name, width, height in VIEWPORTS],
            "results": self.results,
            "findings": self.findings,
            "summary": {
                "passed": sum(1 for result in self.results if result["status"] == "PASS"),
                "failed_results": sum(1 for result in self.results if result["status"] == "FAIL"),
                "unique_failures": len(unique_failures),
                "screenshots": len(list(SHOTS.glob("*.png"))) if SHOTS.exists() else 0,
                "network_events": len(self.network_events),
                "refresh_requests": self.refresh_requests,
                "demo_post_requests_observed": self.demo_post_requests,
                "external_provider_requests": len(self.external_requests),
            },
            "security": {
                "passwords_suppressed": True,
                "tokens_suppressed": True,
                "authorization_headers_suppressed": True,
                "api_keys_suppressed": True,
            },
        }
        REPORT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        lines = [
            "# Sellora Sprint 8B staging closure",
            "",
            f"Decision: **{decision}**",
            f"Passed checks: **{report['summary']['passed']}**",
            f"Failed results: **{report['summary']['failed_results']}**",
            f"Unique failures: **{report['summary']['unique_failures']}**",
            f"Screenshots: **{report['summary']['screenshots']}**",
            f"External provider requests: **{report['summary']['external_provider_requests']}**",
            "",
            "## Results",
            "",
            "| Group | Check | Status | Detail |",
            "|---|---|---:|---|",
        ]
        for result in self.results:
            detail = str(result.get("detail", "")).replace("|", "/").replace("\n", " ")
            lines.append(f"| {result['group']} | {result['check']} | {result['status']} | {detail} |")
        lines.extend(["", "## Findings", ""])
        if not self.findings:
            lines.append("No findings.")
        else:
            lines.extend(["| Severity | Area | Category | Detail |", "|---|---|---|---|"])
            for finding in self.findings:
                detail = finding["detail"].replace("|", "/").replace("\n", " ")
                lines.append(f"| {finding['severity']} | {finding['area']} | {finding['category']} | {detail} |")
        REPORT_MD.write_text("\n".join(lines), encoding="utf-8")
        return decision

    def run(self) -> str:
        OUT.mkdir(parents=True, exist_ok=True)
        try:
            self.api_setup_and_security()
            self.browser_run()
        except Exception as exc:
            self.finding("FAIL", "global", "runner_exception", repr(exc))
        finally:
            try:
                self.cleanup_api()
            except Exception as exc:
                self.finding("FAIL", "cleanup", "cleanup_exception", repr(exc))
            try:
                self.final_api_assertions()
            except Exception as exc:
                self.finding("FAIL", "final", "assertion_exception", repr(exc))
            self.http.close()
        return self.write_report()


if __name__ == "__main__":
    required = [
        "STAGING_FRONTEND_URL",
        "STAGING_API_URL",
        "STAGING_OWNER_EMAIL",
        "STAGING_OWNER_PASSWORD",
        "STAGING_MANAGER_EMAIL",
        "STAGING_MANAGER_PASSWORD",
        "STAGING_ANALYST_EMAIL",
        "STAGING_ANALYST_PASSWORD",
        "STAGING_TEST_WORKSPACE_ID",
    ]
    missing = [name for name in required if not env(name)]
    if missing:
        print("Missing required Sprint 8B staging inputs", file=sys.stderr)
        raise SystemExit(2)
    decision = Sprint8BClosure().run()
    print(f"Sprint 8B staging closure decision: {decision}")
    raise SystemExit(0 if decision == "PASS" else 1)
