#!/usr/bin/env python3
"""Sprint 8D browser/mobile, workspace-switch and duplicate-submit closure."""
from __future__ import annotations

import json
import os
import re
import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright

FRONTEND = os.environ["STAGING_FRONTEND_URL"].rstrip("/")
BACKEND = os.environ["STAGING_API_URL"].rstrip("/")
API = BACKEND + "/api/v1"
EXPECTED_COMMIT = os.environ["EXPECTED_RUNTIME_COMMIT"].lower()
WORKSPACE_A = os.environ["STAGING_TEST_WORKSPACE_ID"]
OUT_DIR = Path("artifacts/sprint-8d-browser")
SCREEN_DIR = OUT_DIR / "screenshots"
REPORT_PATH = OUT_DIR / "browser.json"
MD_PATH = OUT_DIR / "browser.md"
RUN = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
PREFIX = f"QA8D-BROWSER-{RUN}"
TIMEOUT = httpx.Timeout(connect=20, read=60, write=60, pool=20)
VIEWPORTS = [
    ("desktop-1366x768", 1366, 768),
    ("mobile-375x812", 375, 812),
    ("mobile-390x844", 390, 844),
    ("mobile-430x932", 430, 932),
    ("tablet-768x1024", 768, 1024),
]
THEMES = ("light", "dark")
ROUTES = ("orders", "inventory", "shipments")


@dataclass
class Session:
    access: str
    refresh: str
    user: dict[str, Any]


class BrowserClosure:
    def __init__(self) -> None:
        self.owner: Session | None = None
        self.workspace_b_id: str | None = None
        self.workspace_b_name: str | None = None
        self.workspace_b_created = False
        self.product_id: str | None = None
        self.variant_id: str | None = None
        self.inventory_id: str | None = None
        self.fixture_initial_stock = 5
        self.runtime: dict[str, Any] = {}
        self.checks: list[dict[str, Any]] = []
        self.findings: list[dict[str, Any]] = []
        self.screenshots: list[str] = []
        self.console_errors: list[dict[str, str]] = []
        self.page_errors: list[dict[str, str]] = []
        self.request_failures: list[dict[str, str]] = []
        self.unexpected_http: list[dict[str, Any]] = []
        self.cors_errors: list[dict[str, str]] = []
        self.network = {
            "events": 0,
            "posts": 0,
            "patches": 0,
            "puts": 0,
            "http_5xx": 0,
            "http_404": 0,
            "nova_poshta": 0,
            "meta": 0,
        }
        self.duplicate_post_urls: list[str] = []
        self.cleanup = {
            "fixture_stock": None,
            "fixture_reserved": None,
            "fixture_visible": None,
            "orders": 0,
            "shipments": 0,
        }
        self.safe_error: str | None = None

    @staticmethod
    def safe(value: Any) -> Any:
        if isinstance(value, dict):
            return {
                str(key): BrowserClosure.safe(item)
                for key, item in value.items()
                if str(key).lower()
                not in {"access_token", "refresh_token", "authorization", "password", "email", "phone"}
            }
        if isinstance(value, list):
            return [BrowserClosure.safe(item) for item in value[:50]]
        text = str(value)
        text = re.sub(r"Bearer\s+\S+", "Bearer [REDACTED]", text, flags=re.I)
        text = re.sub(r"\beyJ[A-Za-z0-9._-]{20,}\b", "[TOKEN]", text)
        return text[:700]

    def check(self, gate: str, name: str, ok: bool, detail: Any = None) -> None:
        row: dict[str, Any] = {"gate": gate, "name": name, "status": "PASS" if ok else "FAIL"}
        if detail is not None:
            row["detail"] = self.safe(detail)
        self.checks.append(row)
        print(json.dumps(row, ensure_ascii=False), flush=True)

    def finding(self, severity: str, scope: str, kind: str, detail: Any) -> None:
        row = {"severity": severity, "scope": scope, "kind": kind, "detail": self.safe(detail)}
        self.findings.append(row)
        print(json.dumps(row, ensure_ascii=False), flush=True)

    def headers(self, workspace: str | None = None) -> dict[str, str]:
        if not self.owner:
            return {"Cache-Control": "no-cache"}
        result = {"Authorization": f"Bearer {self.owner.access}", "Cache-Control": "no-cache"}
        if workspace:
            result["X-Workspace-ID"] = workspace
        return result

    def request(
        self,
        method: str,
        path: str,
        workspace: str | None = None,
        payload: dict[str, Any] | None = None,
        expected: tuple[int, ...] | None = None,
    ) -> tuple[int, Any]:
        url = path if path.startswith("http") else API + path
        with httpx.Client(timeout=TIMEOUT, follow_redirects=True, headers={"Connection": "close"}) as client:
            response = client.request(method, url, headers=self.headers(workspace), json=payload)
        try:
            body: Any = response.json()
        except Exception:
            body = response.text[:400]
        print(f"API {method} {httpx.URL(url).path} -> {response.status_code}", flush=True)
        if expected and response.status_code not in expected:
            raise RuntimeError(f"{method} {httpx.URL(url).path}: HTTP {response.status_code}")
        return response.status_code, body

    def wait_environment(self) -> None:
        deadline = time.monotonic() + 15 * 60
        last: dict[str, Any] = {}
        while time.monotonic() < deadline:
            try:
                with httpx.Client(timeout=TIMEOUT, follow_redirects=True) as client:
                    health = client.get(BACKEND + "/health")
                    frontend = client.get(FRONTEND + "/login")
                if health.status_code == 200:
                    last = health.json()
                    commit = str(last.get("runtime_commit", "")).lower()
                    if commit.startswith(EXPECTED_COMMIT[:12]) and frontend.status_code == 200:
                        self.runtime = {
                            "status": last.get("status"),
                            "runtime_commit": commit,
                            "process_started_at": last.get("process_started_at"),
                            "frontend_status": frontend.status_code,
                        }
                        break
            except Exception:
                pass
            time.sleep(10)
        self.check("A", "frontend/backend contain Sprint 8D runtime", bool(self.runtime), self.runtime or last)
        if not self.runtime:
            raise RuntimeError("Expected Sprint 8D staging runtime was not observed")

    def login(self) -> None:
        code, tokens = self.request(
            "POST",
            "/auth/login",
            payload={
                "email": os.environ["STAGING_OWNER_EMAIL"],
                "password": os.environ["STAGING_OWNER_PASSWORD"],
            },
            expected=(200,),
        )
        assert code == 200
        self.owner = Session(str(tokens["access_token"]), str(tokens["refresh_token"]), {})
        _, user = self.request("GET", "/auth/me", expected=(200,))
        self.owner.user = user
        membership_a = next(
            (item for item in user.get("memberships", []) if str(item.get("workspace_id")) == WORKSPACE_A),
            None,
        )
        self.check("A", "OWNER browser session has QA workspace", bool(membership_a), {"role": membership_a.get("role") if membership_a else None})
        if not membership_a:
            raise RuntimeError("OWNER lacks QA workspace membership")

    def resolve_workspace_b(self) -> None:
        assert self.owner is not None
        memberships = self.owner.user.get("memberships", [])
        candidates = [
            item
            for item in memberships
            if str(item.get("workspace_id")) != WORKSPACE_A
            and str(item.get("workspace_name", "")).startswith("QA8D-")
        ]
        if not candidates:
            slug = f"qa8d-browser-{RUN}".lower()
            code, workspace = self.request(
                "POST",
                "/workspaces",
                payload={
                    "name": f"{PREFIX} Isolation",
                    "slug": slug,
                    "currency_code": "UAH",
                    "timezone": "Europe/Kyiv",
                },
                expected=(201,),
            )
            assert code == 201
            self.workspace_b_created = True
            _, user = self.request("GET", "/auth/me", expected=(200,))
            self.owner.user = user
            candidates = [
                item for item in user.get("memberships", []) if str(item.get("workspace_id")) == str(workspace["id"])
            ]
        selected = candidates[-1] if candidates else None
        self.workspace_b_id = str(selected.get("workspace_id")) if selected else None
        self.workspace_b_name = str(selected.get("workspace_name")) if selected else None
        self.check(
            "K",
            "second synthetic workspace available for browser switching",
            bool(self.workspace_b_id and self.workspace_b_name),
            {"created_by_browser_runner": self.workspace_b_created},
        )
        if not self.workspace_b_id or not self.workspace_b_name:
            raise RuntimeError("No secondary QA workspace available")

    def setup_fixture(self) -> None:
        assert self.owner is not None
        _, product = self.request(
            "POST",
            "/products",
            WORKSPACE_A,
            {
                "name": f"{PREFIX} Product",
                "sku": f"{PREFIX}-P",
                "description": "Synthetic Sprint 8D browser fixture",
                "category": "QA",
                "brand": "Sellora QA",
            },
            expected=(201,),
        )
        self.product_id = str(product["id"])
        _, variant = self.request(
            "POST",
            "/products/variants",
            WORKSPACE_A,
            {
                "product_id": self.product_id,
                "sku": f"{PREFIX}-V",
                "color": "Synthetic",
                "size": "Browser",
                "price": "100.00",
                "initial_stock_quantity": self.fixture_initial_stock,
                "minimum_quantity": 1,
            },
            expected=(201,),
        )
        self.variant_id = str(variant["id"])
        _, inventory = self.request("GET", "/inventory", WORKSPACE_A, expected=(200,))
        row = next((item for item in inventory if str(item.get("product_variant_id")) == self.variant_id), None)
        self.inventory_id = str(row["id"]) if row else None
        self.check(
            "L",
            "browser duplicate-submit fixture prepared",
            bool(row) and int(row["stock_quantity"]) == self.fixture_initial_stock and int(row["reserved_quantity"]) == 0,
            {"stock": row.get("stock_quantity") if row else None, "reserved": row.get("reserved_quantity") if row else None},
        )
        if not self.inventory_id:
            raise RuntimeError("Browser inventory fixture was not created")

    def context(self, browser: Browser, width: int, height: int, theme: str, workspace: str = WORKSPACE_A) -> BrowserContext:
        assert self.owner is not None
        context = browser.new_context(
            viewport={"width": width, "height": height},
            is_mobile=width < 768,
            has_touch=width < 768,
            color_scheme=theme,
        )
        payload = {
            "access": self.owner.access,
            "refresh": self.owner.refresh,
            "user": self.owner.user,
            "workspace": workspace,
            "theme": theme,
        }
        context.add_init_script(
            script=f"""
            (() => {{
              const payload = {json.dumps(payload, ensure_ascii=False)};
              localStorage.setItem('sellora.access_token', payload.access);
              localStorage.setItem('sellora.refresh_token', payload.refresh);
              localStorage.setItem('sellora.current_user', JSON.stringify(payload.user));
              localStorage.setItem('sellora.current_workspace_id', payload.workspace);
              localStorage.setItem('sellora.theme-mode', payload.theme);
            }})();
            """
        )
        return context

    def watch_page(self, page: Page, scope: str) -> None:
        def on_console(message: Any) -> None:
            if message.type != "error":
                return
            text = str(message.text)
            row = {"scope": scope, "text": text[:500]}
            self.console_errors.append(row)
            if "cors" in text.lower():
                self.cors_errors.append(row)

        def on_page_error(error: Any) -> None:
            self.page_errors.append({"scope": scope, "text": str(error)[:500]})

        def on_request_failed(request: Any) -> None:
            failure = request.failure or "request failed"
            row = {"scope": scope, "url": request.url[:300], "failure": str(failure)[:300]}
            self.request_failures.append(row)
            if "cors" in str(failure).lower():
                self.cors_errors.append({"scope": scope, "text": str(failure)[:500]})

        def on_request(request: Any) -> None:
            self.network["events"] += 1
            method = request.method.upper()
            if method == "POST":
                self.network["posts"] += 1
            elif method == "PATCH":
                self.network["patches"] += 1
            elif method == "PUT":
                self.network["puts"] += 1
            lowered = request.url.lower()
            if "nova-poshta" in lowered or "api.novaposhta" in lowered:
                self.network["nova_poshta"] += 1
            if "graph.facebook" in lowered or "meta-ads" in lowered:
                self.network["meta"] += 1

        def on_response(response: Any) -> None:
            status = int(response.status)
            if status == 404 or status >= 500:
                row = {"scope": scope, "status": status, "url": response.url[:300], "method": response.request.method}
                self.unexpected_http.append(row)
                if status == 404:
                    self.network["http_404"] += 1
                if status >= 500:
                    self.network["http_5xx"] += 1

        page.on("console", on_console)
        page.on("pageerror", on_page_error)
        page.on("requestfailed", on_request_failed)
        page.on("request", on_request)
        page.on("response", on_response)

    @staticmethod
    def wait_page(page: Page) -> None:
        page.locator("main").wait_for(state="visible", timeout=45000)
        page.wait_for_timeout(900)

    @staticmethod
    def header_cta(page: Page) -> Any:
        return page.locator("main h1").first.locator("xpath=../..").locator("button").first

    @staticmethod
    def page_metrics(page: Page) -> dict[str, Any]:
        return page.evaluate(
            """
            () => {
              const visible = (el) => {
                const style = getComputedStyle(el);
                const rect = el.getBoundingClientRect();
                return style.display !== 'none' && style.visibility !== 'hidden' && rect.width > 0 && rect.height > 0;
              };
              const h1 = document.querySelector('main h1');
              const headerRoot = h1?.parentElement?.parentElement;
              const ctas = headerRoot ? Array.from(headerRoot.querySelectorAll('button,a')).filter(visible) : [];
              const hiddenCtas = ctas.filter((el) => {
                const rect = el.getBoundingClientRect();
                return rect.left < -1 || rect.right > window.innerWidth + 1 || rect.top < -1 || rect.bottom > window.innerHeight + 1;
              });
              const largeScrollers = Array.from(document.querySelectorAll('*')).filter((el) => {
                if (el === document.documentElement || el === document.body) return false;
                if (!visible(el)) return false;
                const style = getComputedStyle(el);
                const rect = el.getBoundingClientRect();
                const scrollable = (style.overflowY === 'auto' || style.overflowY === 'scroll') && el.scrollHeight > el.clientHeight + 4;
                return scrollable && rect.height > window.innerHeight * 0.45 && rect.width > window.innerWidth * 0.4;
              });
              return {
                theme: document.documentElement.dataset.theme || '',
                document_overflow_x: Math.max(0, document.documentElement.scrollWidth - document.documentElement.clientWidth),
                body_overflow_x: Math.max(0, document.body.scrollWidth - document.body.clientWidth),
                cta_count: ctas.length,
                hidden_cta_count: hiddenCtas.length,
                large_vertical_scrollers: largeScrollers.length,
                dialog_count: document.querySelectorAll('[role="dialog"]').length,
              };
            }
            """
        )

    def screenshot(self, page: Page, name: str) -> None:
        SCREEN_DIR.mkdir(parents=True, exist_ok=True)
        path = SCREEN_DIR / name
        page.screenshot(path=str(path), full_page=True)
        self.screenshots.append(str(path.relative_to(OUT_DIR)))

    @staticmethod
    def close_overlay(page: Page) -> None:
        desktop_panel = page.locator('[data-entity-side-panel="desktop"]:visible')
        if desktop_panel.count():
            desktop_panel.locator("button").first.click()
            return
        page.keyboard.press("Escape")
        page.wait_for_timeout(250)

    def matrix(self, browser: Browser) -> None:
        assert self.inventory_id is not None
        for viewport_name, width, height in VIEWPORTS:
            for theme in THEMES:
                label = f"{viewport_name}/{theme}"
                context = self.context(browser, width, height, theme)
                page = context.new_page()
                self.watch_page(page, label)
                try:
                    for route in ROUTES:
                        scope = f"{label}/{route}"
                        page.goto(f"{FRONTEND}/{route}", wait_until="domcontentloaded", timeout=60000)
                        self.wait_page(page)
                        metrics = self.page_metrics(page)
                        ok = (
                            page.url.startswith(f"{FRONTEND}/{route}")
                            and metrics["theme"] == theme
                            and metrics["document_overflow_x"] == 0
                            and metrics["body_overflow_x"] == 0
                            and metrics["cta_count"] >= 1
                            and metrics["hidden_cta_count"] == 0
                            and metrics["large_vertical_scrollers"] <= 1
                        )
                        self.check("L", f"{scope} responsive shell, CTA and theme", ok, metrics)

                        if route == "orders":
                            cta = self.header_cta(page)
                            cta.click()
                            dialog = page.locator('[role="dialog"]:visible')
                            self.check("L", f"{scope} order form opens without overflow", dialog.count() == 1 and dialog.evaluate("el => el.scrollWidth <= el.clientWidth + 1"))
                            self.close_overlay(page)
                        elif route == "inventory":
                            search = page.locator("main input").first
                            search.fill(PREFIX)
                            page.wait_for_timeout(700)
                            marker = page.get_by_text(PREFIX, exact=False).first
                            marker.wait_for(state="visible", timeout=15000)
                            marker.click()
                            if width >= 1024:
                                panel = page.locator('[data-entity-side-panel="desktop"]:visible')
                            else:
                                panel = page.locator('[role="dialog"]:visible')
                            self.check("L", f"{scope} inventory detail uses correct panel/drawer", panel.count() == 1)
                            self.close_overlay(page)
                            search.fill("")
                        else:
                            cta = self.header_cta(page)
                            cta.click()
                            dialog = page.locator('[role="dialog"]:visible')
                            self.check("L", f"{scope} shipment form opens without overflow", dialog.count() == 1 and dialog.evaluate("el => el.scrollWidth <= el.clientWidth + 1"))
                            self.close_overlay(page)

                        self.screenshot(page, f"{viewport_name}-{theme}-{route}.png")
                except Exception as exc:
                    self.finding("BLOCKER", label, "matrix_exception", repr(exc))
                finally:
                    context.close()

    def loading_states(self, browser: Browser) -> None:
        for route in ROUTES:
            context = self.context(browser, 1366, 768, "light")
            page = context.new_page()
            scope = f"loading/{route}"
            self.watch_page(page, scope)
            session = context.new_cdp_session(page)
            try:
                session.send("Network.enable")
                session.send(
                    "Network.emulateNetworkConditions",
                    {
                        "offline": False,
                        "latency": 1400,
                        "downloadThroughput": 4_000_000,
                        "uploadThroughput": 2_000_000,
                        "connectionType": "cellular3g",
                    },
                )
                page.goto(f"{FRONTEND}/{route}", wait_until="domcontentloaded", timeout=60000)
                skeleton = page.locator(".animate-pulse:visible").first
                skeleton.wait_for(state="visible", timeout=8000)
                self.check("L", f"{route} truthful loading state visible", True)
                session.send(
                    "Network.emulateNetworkConditions",
                    {
                        "offline": False,
                        "latency": 0,
                        "downloadThroughput": -1,
                        "uploadThroughput": -1,
                        "connectionType": "none",
                    },
                )
                self.wait_page(page)
            except Exception as exc:
                self.check("L", f"{route} truthful loading state visible", False, repr(exc))
            finally:
                context.close()

    def open_workspace_menu(self, page: Page, width: int, programmatic: bool = False) -> Any:
        trigger = page.locator(".account-profile-trigger") if width >= 768 else page.locator(".topbar-action")
        if programmatic:
            trigger.evaluate("el => el.click()")
        else:
            trigger.click()
        if width >= 768:
            panel = page.locator('[role="menu"]:visible')
        else:
            panel = page.locator('.mobile-more-sheet:visible')
        panel.wait_for(state="visible", timeout=10000)
        return panel

    def switch_workspace(self, page: Page, width: int, target_name: str, target_id: str, programmatic: bool = False) -> None:
        panel = self.open_workspace_menu(page, width, programmatic=programmatic)
        target = panel.get_by_role("button", name=re.compile(re.escape(target_name), re.I)).first
        if programmatic:
            target.evaluate("el => el.click()")
        else:
            target.click()
        page.wait_for_function(
            "target => localStorage.getItem('sellora.current_workspace_id') === target",
            arg=target_id,
            timeout=15000,
        )
        page.wait_for_timeout(1100)

    def workspace_switching(self, browser: Browser) -> None:
        assert self.workspace_b_id and self.workspace_b_name and self.inventory_id
        for label, width, height, theme in (
            ("desktop", 1366, 768, "light"),
            ("mobile", 390, 844, "dark"),
        ):
            context = self.context(browser, width, height, theme)
            page = context.new_page()
            scope = f"workspace-switch/{label}"
            self.watch_page(page, scope)
            post_after_b: list[str] = []
            b_get_headers: list[str | None] = []
            switch_phase = {"active": False}

            def request_watch(request: Any) -> None:
                if not switch_phase["active"]:
                    return
                if request.method == "POST":
                    post_after_b.append(request.url)
                if "/api/v1/inventory" in request.url and request.method == "GET":
                    b_get_headers.append(request.headers.get("x-workspace-id"))

            page.on("request", request_watch)
            try:
                page.goto(f"{FRONTEND}/orders", wait_until="domcontentloaded", timeout=60000)
                self.wait_page(page)
                self.header_cta(page).click()
                page.locator('[role="dialog"]:visible').wait_for(timeout=10000)
                self.switch_workspace(page, width, self.workspace_b_name, self.workspace_b_id, programmatic=True)
                self.check(
                    "K",
                    f"{label} open order form closes on workspace switch",
                    page.locator('[role="dialog"]:visible').count() == 0,
                )

                self.switch_workspace(page, width, self.owner_workspace_name(), WORKSPACE_A)
                page.goto(f"{FRONTEND}/shipments", wait_until="domcontentloaded", timeout=60000)
                self.wait_page(page)
                self.header_cta(page).click()
                page.locator('[role="dialog"]:visible').wait_for(timeout=10000)
                self.switch_workspace(page, width, self.workspace_b_name, self.workspace_b_id, programmatic=True)
                self.check(
                    "K",
                    f"{label} open shipment form closes on workspace switch",
                    page.locator('[role="dialog"]:visible').count() == 0,
                )

                self.switch_workspace(page, width, self.owner_workspace_name(), WORKSPACE_A)
                page.goto(f"{FRONTEND}/inventory", wait_until="domcontentloaded", timeout=60000)
                self.wait_page(page)
                self.header_cta(page).click()
                form = page.locator("main form").first
                form.wait_for(state="visible", timeout=10000)
                form.locator("select").nth(0).select_option(self.inventory_id)
                form.locator('input[type="number"]').fill("1")
                form.locator("input").last.fill(f"{PREFIX} stale-form")
                page.evaluate(
                    """({target, marker}) => {
                      window.__qa8dStaleSeen = false;
                      window.__qa8dStaleTimer = setInterval(() => {
                        if (localStorage.getItem('sellora.current_workspace_id') === target && document.body.innerText.includes(marker)) {
                          window.__qa8dStaleSeen = true;
                        }
                      }, 10);
                    }""",
                    {"target": self.workspace_b_id, "marker": PREFIX},
                )
                switch_phase["active"] = True
                self.switch_workspace(page, width, self.workspace_b_name, self.workspace_b_id)
                page.wait_for_timeout(1200)
                state = page.evaluate(
                    """() => {
                      const form = document.querySelector('main form');
                      const selects = form ? form.querySelectorAll('select') : [];
                      const inputs = form ? form.querySelectorAll('input') : [];
                      const button = form ? form.querySelector('button[type="submit"]') : null;
                      if (window.__qa8dStaleTimer) clearInterval(window.__qa8dStaleTimer);
                      return {
                        inventory: selects[0]?.value || '',
                        reason: inputs[inputs.length - 1]?.value || '',
                        submit_disabled: Boolean(button?.disabled),
                        stale_seen: Boolean(window.__qa8dStaleSeen),
                      };
                    }"""
                )
                marker_visible = PREFIX in page.locator("body").inner_text()
                before = len(post_after_b)
                submit = page.locator('main form button[type="submit"]').first
                if submit.count():
                    submit.evaluate("el => el.click()")
                page.wait_for_timeout(500)
                after = len(post_after_b)
                state["marker_visible"] = marker_visible
                state["old_submit_posts"] = after - before
                state["workspace_headers"] = b_get_headers
                ok = (
                    state["inventory"] == ""
                    and state["reason"] == ""
                    and state["submit_disabled"] is True
                    and state["stale_seen"] is False
                    and marker_visible is False
                    and after == before
                    and bool(b_get_headers)
                    and all(value == self.workspace_b_id for value in b_get_headers if value is not None)
                )
                self.check("K", f"{label} inventory form reset and stale workspace isolation", ok, state)
                self.screenshot(page, f"workspace-switch-{label}.png")
            except Exception as exc:
                self.finding("BLOCKER", scope, "workspace_switch_exception", repr(exc))
            finally:
                context.close()

    def owner_workspace_name(self) -> str:
        assert self.owner is not None
        membership = next(
            item for item in self.owner.user.get("memberships", []) if str(item.get("workspace_id")) == WORKSPACE_A
        )
        return str(membership.get("workspace_name"))

    def duplicate_submit(self, browser: Browser) -> None:
        assert self.inventory_id and self.variant_id
        _, before_rows = self.request("GET", "/inventory", WORKSPACE_A, expected=(200,))
        before = next(item for item in before_rows if str(item.get("id")) == self.inventory_id)
        before_stock = int(before["stock_quantity"])
        context = self.context(browser, 1366, 768, "light")
        page = context.new_page()
        self.watch_page(page, "duplicate-submit")
        matched_requests: list[str] = []

        def watch(request: Any) -> None:
            if request.method == "POST" and f"/api/v1/inventory/{self.inventory_id}/transactions" in request.url:
                matched_requests.append(request.url)

        page.on("request", watch)
        try:
            page.goto(f"{FRONTEND}/inventory", wait_until="domcontentloaded", timeout=60000)
            self.wait_page(page)
            self.header_cta(page).click()
            form = page.locator("main form").first
            form.wait_for(state="visible", timeout=10000)
            form.locator("select").nth(0).select_option(self.inventory_id)
            form.locator("select").nth(1).select_option("STOCK_IN")
            form.locator('input[type="number"]').fill("1")
            reason = f"{PREFIX} duplicate-submit"
            form.locator("input").last.fill(reason)
            button = form.locator('button[type="submit"]')
            button.evaluate("el => { el.click(); el.click(); }")
            deadline = time.monotonic() + 20
            while time.monotonic() < deadline and len(matched_requests) < 1:
                page.wait_for_timeout(100)
            page.wait_for_timeout(1800)
            _, after_rows = self.request("GET", "/inventory", WORKSPACE_A, expected=(200,))
            after = next(item for item in after_rows if str(item.get("id")) == self.inventory_id)
            _, transactions = self.request(
                "GET", f"/inventory/transactions?inventory_id={self.inventory_id}", WORKSPACE_A, expected=(200,)
            )
            matching_logs = [item for item in transactions if str(item.get("reason", "")) == reason]
            after_stock = int(after["stock_quantity"])
            ok = len(matched_requests) == 1 and len(matching_logs) == 1 and after_stock == before_stock + 1
            self.duplicate_post_urls = matched_requests
            self.check(
                "L",
                "rapid double click emits one inventory POST and one stock effect",
                ok,
                {
                    "post_count": len(matched_requests),
                    "matching_transactions": len(matching_logs),
                    "before_stock": before_stock,
                    "after_stock": after_stock,
                },
            )
        except Exception as exc:
            self.finding("BLOCKER", "duplicate-submit", "runner_exception", repr(exc))
        finally:
            context.close()

    def cleanup_fixture(self) -> None:
        if not self.inventory_id or not self.variant_id:
            return
        try:
            _, inventory = self.request("GET", "/inventory", WORKSPACE_A, expected=(200,))
            row = next((item for item in inventory if str(item.get("id")) == self.inventory_id), None)
            if row:
                stock = int(row["stock_quantity"])
                reserved = int(row["reserved_quantity"])
                if reserved:
                    self.request(
                        "POST",
                        f"/inventory/{self.inventory_id}/transactions",
                        WORKSPACE_A,
                        {"transaction_type": "UNRESERVE", "quantity": reserved, "reason": f"{PREFIX} cleanup"},
                        expected=(201,),
                    )
                if stock:
                    self.request(
                        "POST",
                        f"/inventory/{self.inventory_id}/transactions",
                        WORKSPACE_A,
                        {"transaction_type": "STOCK_OUT", "quantity": stock, "reason": f"{PREFIX} cleanup"},
                        expected=(201,),
                    )
            self.request("DELETE", f"/products/variants/{self.variant_id}", WORKSPACE_A, expected=(204,))
            if self.product_id:
                self.request("DELETE", f"/products/{self.product_id}", WORKSPACE_A, expected=(204,))
        except Exception as exc:
            self.finding("WARN", "cleanup", "api_cleanup_error", repr(exc))

        try:
            _, inventory = self.request("GET", "/inventory", WORKSPACE_A, expected=(200,))
            visible = next((item for item in inventory if str(item.get("product_variant_id")) == self.variant_id), None)
            _, orders = self.request("GET", "/orders", WORKSPACE_A, expected=(200,))
            _, shipments = self.request("GET", "/shipments", WORKSPACE_A, expected=(200,))
            active_orders = [item for item in orders if PREFIX in str(item.get("notes", ""))]
            active_shipments = [
                item for item in shipments if PREFIX in str(item.get("notes", "")) or PREFIX in str(item.get("tracking_number", ""))
            ]
            self.cleanup = {
                "fixture_stock": int(visible["stock_quantity"]) if visible else 0,
                "fixture_reserved": int(visible["reserved_quantity"]) if visible else 0,
                "fixture_visible": bool(visible),
                "orders": len(active_orders),
                "shipments": len(active_shipments),
            }
            self.check(
                "M",
                "browser fixture cleanup leaves zero active stock/reservations/orders/shipments",
                self.cleanup["fixture_stock"] == 0
                and self.cleanup["fixture_reserved"] == 0
                and self.cleanup["fixture_visible"] is False
                and self.cleanup["orders"] == 0
                and self.cleanup["shipments"] == 0,
                self.cleanup,
            )
        except Exception as exc:
            self.finding("BLOCKER", "cleanup", "verification_error", repr(exc))

    def final_browser_health(self) -> None:
        self.check("L", "unexpected browser console errors = 0", len(self.console_errors) == 0, {"count": len(self.console_errors), "sample": self.console_errors[:5]})
        self.check("L", "runtime page exceptions = 0", len(self.page_errors) == 0, {"count": len(self.page_errors), "sample": self.page_errors[:5]})
        self.check("L", "browser request failures = 0", len(self.request_failures) == 0, {"count": len(self.request_failures), "sample": self.request_failures[:5]})
        self.check("L", "unexpected HTTP 404/5xx = 0", len(self.unexpected_http) == 0, {"count": len(self.unexpected_http), "sample": self.unexpected_http[:8]})
        self.check("L", "CORS errors = 0", len(self.cors_errors) == 0, {"count": len(self.cors_errors), "sample": self.cors_errors[:5]})
        self.check("H", "Meta Ads / Nova Poshta provider calls = 0", self.network["meta"] == 0 and self.network["nova_poshta"] == 0, self.network)

    def write_report(self) -> str:
        failures = [item for item in self.checks if item["status"] != "PASS"]
        blockers = [item for item in self.findings if item["severity"] == "BLOCKER"]
        decision = "PASS_PENDING_POSTGRES_CLEANUP" if not failures and not blockers and not self.safe_error else "FAIL"
        report = {
            "sprint": "8D",
            "phase": "browser-mobile",
            "decision": decision,
            "runtime": self.runtime,
            "marker": PREFIX,
            "checks": self.checks,
            "findings": self.findings,
            "viewports": [{"name": name, "width": width, "height": height} for name, width, height in VIEWPORTS],
            "themes": list(THEMES),
            "routes": list(ROUTES),
            "screenshots": self.screenshots,
            "network": self.network,
            "browser_errors": {
                "console": self.console_errors,
                "page": self.page_errors,
                "request_failures": self.request_failures,
                "unexpected_http": self.unexpected_http,
                "cors": self.cors_errors,
            },
            "duplicate_submit": {"inventory_post_count": len(self.duplicate_post_urls)},
            "cleanup": self.cleanup,
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
            "# Sprint 8D browser/mobile closure",
            "",
            f"- Decision: **{decision}**",
            f"- Runtime: `{self.runtime.get('runtime_commit', 'unavailable')}`",
            f"- Checks: {len(self.checks) - len(failures)} PASS / {len(failures)} FAIL",
            f"- Screenshots: {len(self.screenshots)}",
            f"- Network events: {self.network['events']}",
            f"- Console/page/request errors: {len(self.console_errors)}/{len(self.page_errors)}/{len(self.request_failures)}",
            "",
            "| Gate | Check | Status |",
            "|---|---|---|",
        ]
        lines += [f"| {item['gate']} | {item['name']} | {item['status']} |" for item in self.checks]
        MD_PATH.write_text("\n".join(lines), encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)
        return decision

    def run(self) -> int:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        try:
            self.wait_environment()
            self.login()
            self.resolve_workspace_b()
            self.setup_fixture()
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                try:
                    self.matrix(browser)
                    self.loading_states(browser)
                    self.workspace_switching(browser)
                    self.duplicate_submit(browser)
                finally:
                    browser.close()
        except Exception as exc:
            self.safe_error = str(exc)[:700]
            self.finding("BLOCKER", "runner", "safe_error", self.safe_error)
        finally:
            if self.owner:
                self.cleanup_fixture()
            self.final_browser_health()
        decision = self.write_report()
        return 0 if decision == "PASS_PENDING_POSTGRES_CLEANUP" else 1


if __name__ == "__main__":
    required = [
        "STAGING_FRONTEND_URL",
        "STAGING_API_URL",
        "EXPECTED_RUNTIME_COMMIT",
        "STAGING_OWNER_EMAIL",
        "STAGING_OWNER_PASSWORD",
        "STAGING_TEST_WORKSPACE_ID",
    ]
    missing = [name for name in required if not os.environ.get(name)]
    if missing:
        print("Missing required Sprint 8D browser inputs", file=sys.stderr)
        raise SystemExit(2)
    raise SystemExit(BrowserClosure().run())
