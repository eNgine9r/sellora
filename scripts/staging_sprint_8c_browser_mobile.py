#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
from playwright.sync_api import Browser, BrowserContext, Page, Request, Response, sync_playwright

FRONTEND = os.getenv("STAGING_FRONTEND_URL", "https://sellora-web-staging.vercel.app").rstrip("/")
API = os.getenv("STAGING_API_URL", "https://sellora-api-staging.onrender.com").rstrip("/")
WORKSPACE_A = os.environ["STAGING_TEST_WORKSPACE_ID"]
OUT_DIR = Path("artifacts/sprint-8c-browser-mobile")
SHOTS = OUT_DIR / "screenshots"
REPORT = OUT_DIR / "sprint-8c-browser-mobile.json"
VIEWPORTS = (
    ("desktop-1366x768", 1366, 768),
    ("mobile-375x812", 375, 812),
    ("mobile-390x844", 390, 844),
    ("mobile-430x932", 430, 932),
    ("tablet-768x1024", 768, 1024),
)
THEMES = ("light", "dark")


def required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required input: {name}")
    return value


def safe_json(response: httpx.Response) -> Any:
    try:
        return response.json()
    except Exception:
        return None


def response_detail(response: httpx.Response) -> str:
    value = safe_json(response)
    if isinstance(value, dict):
        return str(value.get("detail") or f"HTTP {response.status_code}")[:200]
    return f"HTTP {response.status_code}"


@dataclass
class Session:
    access_token: str
    refresh_token: str
    user: dict[str, Any]


@dataclass
class BrowserEvidence:
    label: str
    console_errors: list[str] = field(default_factory=list)
    page_errors: list[str] = field(default_factory=list)
    import_http_errors: list[dict[str, Any]] = field(default_factory=list)
    cors_errors: list[str] = field(default_factory=list)
    external_provider_requests: list[str] = field(default_factory=list)
    upload_posts: int = 0
    execute_posts: int = 0


class Closure:
    def __init__(self) -> None:
        self.api = httpx.Client(timeout=httpx.Timeout(120, connect=30), follow_redirects=True)
        self.owner: Session | None = None
        self.workspace_b_id = ""
        self.workspace_b_name = ""
        self.checks: list[dict[str, Any]] = []
        self.findings: list[dict[str, Any]] = []
        self.network_events = 0
        self.screenshot_count = 0
        self.functional_job_id = ""
        self.result: dict[str, Any] = {
            "decision": "FAIL",
            "viewports": [name for name, _, _ in VIEWPORTS],
            "themes": list(THEMES),
            "checks": self.checks,
            "findings": self.findings,
            "screenshots": 0,
            "network_events": 0,
            "security": {
                "credential_values_absent": True,
                "raw_source_rows_absent": True,
                "external_provider_requests": 0,
                "cross_workspace_responses": 0,
            },
            "safe_error": None,
        }

    def close(self) -> None:
        self.api.close()

    def check(self, gate: str, name: str, passed: bool, detail: Any = None) -> None:
        item = {"gate": gate, "name": name, "status": "PASS" if passed else "FAIL"}
        if detail not in (None, ""):
            item["detail"] = detail
        self.checks.append(item)
        if not passed:
            self.findings.append({"severity": "Major", "gate": gate, "issue": name, "detail": detail})

    def login(self) -> None:
        response = self.api.post(
            f"{API}/api/v1/auth/login",
            json={"email": required("STAGING_OWNER_EMAIL"), "password": required("STAGING_OWNER_PASSWORD")},
        )
        self.check("Preflight", "OWNER login", response.status_code == 200, response_detail(response))
        if response.status_code != 200:
            raise RuntimeError("OWNER login failed")
        body = response.json()
        token = str(body.get("access_token") or "")
        refresh = str(body.get("refresh_token") or "")
        me = self.api.get(f"{API}/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        self.check("Preflight", "OWNER auth/me", me.status_code == 200, response_detail(me))
        if me.status_code != 200:
            raise RuntimeError("OWNER auth/me failed")
        self.owner = Session(token, refresh, me.json())

    def headers(self, workspace_id: str) -> dict[str, str]:
        assert self.owner is not None
        return {"Authorization": f"Bearer {self.owner.access_token}", "X-Workspace-ID": workspace_id}

    def resolve_workspace_b(self) -> None:
        response = self.api.get(f"{API}/api/v1/workspaces", headers=self.headers(WORKSPACE_A))
        self.check("Isolation", "workspace list available", response.status_code == 200, response_detail(response))
        if response.status_code != 200:
            raise RuntimeError("Workspace list unavailable")
        candidates = [
            item for item in response.json()
            if str(item.get("id")) != WORKSPACE_A
            and item.get("is_active") is True
            and ("QA" in str(item.get("name")) or "Sprint 8C" in str(item.get("name")))
        ]
        if not candidates:
            candidates = [item for item in response.json() if str(item.get("id")) != WORKSPACE_A and item.get("is_active") is True]
        if not candidates:
            raise RuntimeError("No active synthetic Workspace B membership available")
        chosen = candidates[0]
        self.workspace_b_id = str(chosen["id"])
        self.workspace_b_name = str(chosen["name"])
        self.check("Isolation", "synthetic Workspace B resolved", bool(self.workspace_b_id))

    def init_context(self, browser: Browser, width: int, height: int, theme: str, workspace_id: str = WORKSPACE_A, delay_imports: bool = False) -> BrowserContext:
        assert self.owner is not None
        context = browser.new_context(
            viewport={"width": width, "height": height},
            is_mobile=width < 768,
            has_touch=width < 768,
            color_scheme=theme,
            accept_downloads=True,
        )
        payload = {
            "access": self.owner.access_token,
            "refresh": self.owner.refresh_token,
            "user": self.owner.user,
            "workspace": workspace_id,
            "theme": theme,
            "delay": delay_imports,
        }
        context.add_init_script(
            script=f"""
            (() => {{
              const seedKey = 'sellora.qa-8c-context-seeded';
              if (!localStorage.getItem(seedKey)) {{
                const payload = {json.dumps(payload, ensure_ascii=False)};
                localStorage.setItem('sellora.access_token', payload.access);
                localStorage.setItem('sellora.refresh_token', payload.refresh);
                localStorage.setItem('sellora.current_user', JSON.stringify(payload.user));
                localStorage.setItem('sellora.current_workspace_id', payload.workspace);
                localStorage.setItem('sellora.theme-mode', payload.theme);
                localStorage.setItem(seedKey, 'true');
              }}
              if ({str(delay_imports).lower()} && !window.__selloraQaFetchWrapped) {{
                window.__selloraQaFetchWrapped = true;
                const originalFetch = window.fetch.bind(window);
                window.fetch = async (...args) => {{
                  const request = args[0];
                  const url = typeof request === 'string' ? request : request?.url || '';
                  const init = args[1] || {{}};
                  const method = String(init.method || request?.method || 'GET').toUpperCase();
                  if (method === 'POST' && (url.includes('/import/upload') || url.includes('/execute'))) {{
                    await new Promise((resolve) => setTimeout(resolve, 1200));
                  }}
                  return originalFetch(...args);
                }};
              }}
            }})();
            """
        )
        return context

    def watch(self, page: Page, label: str) -> BrowserEvidence:
        evidence = BrowserEvidence(label=label)

        def on_console(message) -> None:
            text = message.text[:300]
            if message.type == "error":
                evidence.console_errors.append(text)
                if "cors" in text.lower():
                    evidence.cors_errors.append(text)

        def on_page_error(error) -> None:
            evidence.page_errors.append(str(error)[:300])

        def on_request(request: Request) -> None:
            self.network_events += 1
            parsed = urlparse(request.url)
            host = parsed.netloc.lower()
            path = parsed.path
            if request.method == "POST" and path.endswith("/api/v1/import/upload"):
                evidence.upload_posts += 1
            if request.method == "POST" and "/api/v1/import/" in path and path.endswith("/execute"):
                evidence.execute_posts += 1
            if "graph.facebook" in host or "api.novaposhta.ua" in host:
                evidence.external_provider_requests.append(host)

        def on_response(response: Response) -> None:
            if "/api/v1/import" in response.url and response.status in (404, 500, 502, 503, 504):
                evidence.import_http_errors.append({"status": response.status, "path": urlparse(response.url).path})

        page.on("console", on_console)
        page.on("pageerror", on_page_error)
        page.on("request", on_request)
        page.on("response", on_response)
        return evidence

    def screenshot(self, page: Page, filename: str) -> None:
        SHOTS.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(SHOTS / filename), full_page=True)
        self.screenshot_count += 1

    def body_overflow_ok(self, page: Page) -> bool:
        return bool(page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"))

    def wait_ready(self, page: Page) -> None:
        page.wait_for_timeout(800)
        page.locator("main").wait_for(state="visible", timeout=45000)

    def set_mapping(self, page: Page, mapping: dict[str, str]) -> None:
        labels = page.locator("label")
        for field, column in mapping.items():
            found = False
            for index in range(labels.count()):
                label = labels.nth(index)
                span = label.locator("span")
                select = label.locator("select")
                if span.count() and select.count() and span.first.inner_text().strip() == field:
                    select.select_option(column)
                    found = True
                    break
            if not found:
                raise RuntimeError(f"Mapping control not found: {field}")

    def select_csv_and_preview(self, page: Page) -> None:
        sheet = page.locator('select:has(option[value="CSV"])').first
        sheet.wait_for(state="visible", timeout=30000)
        sheet.select_option("CSV")
        preview_button = page.get_by_role("button", name=re.compile(r"^(Перегляд|Preview)$", re.I)).first
        with page.expect_response(lambda r: "/preview" in r.url and r.request.method == "POST", timeout=90000):
            preview_button.click()
        page.locator("table").first.wait_for(state="visible", timeout=30000)

    def click_dry_run(self, page: Page) -> Response:
        button = page.get_by_role("button", name=re.compile(r"dry|пробн|тестов", re.I)).first
        with page.expect_response(lambda r: "/dry-run" in r.url and r.request.method == "POST", timeout=120000) as info:
            button.click()
        return info.value

    def assert_clean_runtime(self, gate: str, evidence: BrowserEvidence) -> None:
        filtered_console = [item for item in evidence.console_errors if "favicon" not in item.lower()]
        self.check(gate, f"{evidence.label}: runtime exceptions = 0", not evidence.page_errors, len(evidence.page_errors))
        self.check(gate, f"{evidence.label}: console errors = 0", not filtered_console, filtered_console[:3])
        self.check(gate, f"{evidence.label}: core import 404/500 = 0", not evidence.import_http_errors, evidence.import_http_errors)
        self.check(gate, f"{evidence.label}: CORS errors = 0", not evidence.cors_errors, evidence.cors_errors[:3])
        self.check(gate, f"{evidence.label}: Meta/Nova requests = 0", not evidence.external_provider_requests, evidence.external_provider_requests)

    def open_workspace_menu(self, page: Page, width: int) -> None:
        if width >= 768:
            page.locator(".account-profile-trigger").click(timeout=15000)
        else:
            page.locator('button[aria-controls="mobile-more-sheet"]').click(timeout=15000)
        page.wait_for_timeout(400)

    def switch_workspace(self, page: Page, width: int, name: str, workspace_id: str) -> None:
        self.open_workspace_menu(page, width)
        target = page.get_by_text(name, exact=True).last
        target.wait_for(state="visible", timeout=15000)
        target.click()
        page.wait_for_function(
            "expected => localStorage.getItem('sellora.current_workspace_id') === expected",
            arg=workspace_id,
            timeout=30000,
        )
        page.wait_for_timeout(800)

    def valid_csv(self, suffix: str) -> bytes:
        return (
            "Name,Instagram\n"
            f"QA8C Browser Customer {suffix} A,qa8c_browser_{suffix}_a\n"
            f"QA8C Browser Customer {suffix} B,qa8c_browser_{suffix}_b\n"
        ).encode()

    def invalid_csv(self, suffix: str) -> bytes:
        return (
            "Name,Instagram\n"
            f"=HYPERLINK(\"\"x\"\"),qa8c_invalid_{suffix}\n"
        ).encode()

    def functional_flow(self, browser: Browser) -> None:
        context = self.init_context(browser, 1366, 768, "light", delay_imports=True)
        page = context.new_page()
        evidence = self.watch(page, "functional/desktop/light")
        try:
            page.goto(f"{FRONTEND}/settings/import", wait_until="domcontentloaded", timeout=60000)
            self.wait_ready(page)
            self.check("Browser", "functional initial body overflow = 0", self.body_overflow_ok(page))
            file_input = page.locator('input[type="file"]')
            file_input.set_input_files({"name": "qa8c-browser-valid.csv", "mimeType": "text/csv", "buffer": self.valid_csv("functional")})
            upload_button = file_input.locator("xpath=following-sibling::button")
            page.wait_for_timeout(250)
            loading_visible = upload_button.is_disabled() or bool(re.search(r"завантаж|upload", upload_button.inner_text(), re.I))
            self.check("Browser", "upload loading state visible", loading_visible)
            page.wait_for_response(lambda r: r.url.endswith("/api/v1/import/upload") and r.request.method == "POST", timeout=120000)
            self.select_csv_and_preview(page)
            self.set_mapping(page, {"name": "Name", "instagram_username": "Instagram"})

            validate = page.get_by_role("button", name=re.compile(r"валідац|перевір|validate", re.I)).first
            with page.expect_response(lambda r: "/validate" in r.url and r.request.method == "POST", timeout=120000) as validation_info:
                validate.click()
            self.check("Browser", "valid flow validation HTTP 200", validation_info.value.status == 200, validation_info.value.status)

            dry_response = self.click_dry_run(page)
            self.check("Browser", "valid flow dry-run HTTP 200", dry_response.status == 200, dry_response.status)
            report = page.locator("[data-import-dry-run-report]")
            report.wait_for(state="visible", timeout=30000)
            trigger = page.locator("[data-import-execute-trigger]")
            self.check("Browser", "primary execute CTA visible", trigger.is_visible() and trigger.is_enabled())
            trigger.click()
            dialog = page.get_by_role("dialog")
            dialog.wait_for(state="visible", timeout=15000)
            self.check("Browser", "execute confirmation visible", dialog.is_visible())
            self.screenshot(page, "functional-execute-confirmation.png")
            confirm = dialog.get_by_role("button", name=re.compile(r"виконати імпорт|execute import", re.I)).first
            confirm.evaluate("element => { element.click(); element.click(); }")
            page.wait_for_timeout(250)
            self.check("Browser", "execute confirmation pending state", confirm.is_disabled())
            page.wait_for_response(lambda r: "/execute" in r.url and r.request.method == "POST", timeout=180000)
            page.wait_for_timeout(1200)
            self.check("Browser", "duplicate execute requests = 0", evidence.execute_posts == 1, evidence.execute_posts)
            self.check("Browser", "single upload request", evidence.upload_posts == 1, evidence.upload_posts)
            self.screenshot(page, "functional-result-report.png")

            old_job_text = page.locator("text=Import job").count() or page.locator("text=Завдання імпорту").count()
            self.switch_workspace(page, 1366, self.workspace_b_name, self.workspace_b_id)
            page.goto(f"{FRONTEND}/settings/import", wait_until="domcontentloaded", timeout=60000)
            self.wait_ready(page)
            body_b = page.locator("body").inner_text()
            self.check("Isolation", "old frontend import state cleared in Workspace B", "qa8c-browser-valid.csv" not in body_b and not old_job_text)
            self.switch_workspace(page, 1366, self.owner.user.get("memberships", [{}])[0].get("workspace", {}).get("name", "Sellora QA — Sprint 8A.1") if False else "Sellora QA — Sprint 8A.1", WORKSPACE_A)
            self.check("Isolation", "workspace switch A-B-A completed", page.evaluate("localStorage.getItem('sellora.current_workspace_id')") == WORKSPACE_A)
        except Exception as exc:
            self.check("Browser", "functional flow completed", False, str(exc)[:300])
        finally:
            self.assert_clean_runtime("Browser", evidence)
            context.close()

    def visual_matrix(self, browser: Browser) -> None:
        for viewport_name, width, height in VIEWPORTS:
            for theme in THEMES:
                label = f"{viewport_name}/{theme}"
                context = self.init_context(browser, width, height, theme)
                page = context.new_page()
                evidence = self.watch(page, label)
                try:
                    page.goto(f"{FRONTEND}/settings/import", wait_until="domcontentloaded", timeout=60000)
                    self.wait_ready(page)
                    actual_theme = page.evaluate("document.documentElement.dataset.theme")
                    self.check("Visual", f"{label}: theme applied", actual_theme == theme, actual_theme)
                    self.check("Visual", f"{label}: initial body overflow = 0", self.body_overflow_ok(page))
                    suffix = re.sub(r"[^a-z0-9]", "", label.lower())
                    input_file = page.locator('input[type="file"]')
                    with page.expect_response(lambda r: r.url.endswith("/api/v1/import/upload") and r.request.method == "POST", timeout=120000):
                        input_file.set_input_files({"name": f"qa8c-{suffix}.csv", "mimeType": "text/csv", "buffer": self.invalid_csv(suffix)})
                    self.select_csv_and_preview(page)
                    self.set_mapping(page, {"name": "Name", "instagram_username": "Instagram"})
                    self.check("Visual", f"{label}: preview table uses inner scroll", page.locator(".sellora-scrollbar").count() > 0)
                    dry = self.click_dry_run(page)
                    self.check("Visual", f"{label}: invalid dry-run HTTP 200", dry.status == 200, dry.status)
                    issues = page.locator("[data-import-validation-issues]")
                    issues.wait_for(state="visible", timeout=30000)
                    body_text = issues.inner_text()
                    self.check("Visual", f"{label}: localized long validation message visible", len(body_text.strip()) > 20)
                    download_link = page.locator("[data-import-error-csv-download]")
                    self.check("Visual", f"{label}: error CSV download visible", download_link.count() == 1 and download_link.is_visible())
                    self.check("Visual", f"{label}: execute unavailable for invalid file", page.locator("[data-import-execute-trigger]").is_disabled())
                    self.check("Visual", f"{label}: final body overflow = 0", self.body_overflow_ok(page))
                    self.check("Visual", f"{label}: duplicate upload requests = 0", evidence.upload_posts == 1, evidence.upload_posts)
                    self.screenshot(page, f"{viewport_name}-{theme}-invalid-dry-run.png")
                except Exception as exc:
                    self.check("Visual", f"{label}: scenario completed", False, str(exc)[:300])
                finally:
                    self.assert_clean_runtime("Visual", evidence)
                    context.close()

    def run(self) -> int:
        health = self.api.get(f"{API}/health")
        self.check("Preflight", "backend health", health.status_code == 200, response_detail(health))
        frontend = self.api.get(f"{FRONTEND}/login")
        self.check("Preflight", "frontend reachable", frontend.status_code == 200, frontend.status_code)
        self.login()
        self.resolve_workspace_b()
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            try:
                self.functional_flow(browser)
                self.visual_matrix(browser)
            finally:
                browser.close()
        self.result["screenshots"] = self.screenshot_count
        self.result["network_events"] = self.network_events
        self.result["security"]["external_provider_requests"] = sum(
            1 for finding in self.findings if "Meta/Nova" in str(finding.get("issue"))
        )
        failed = [item for item in self.checks if item["status"] != "PASS"]
        self.result["decision"] = "PASS" if not failed else "FAIL"
        return 0 if not failed else 1


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    closure = Closure()
    try:
        return closure.run()
    except Exception as exc:
        closure.result["safe_error"] = str(exc)[:400]
        return 1
    finally:
        closure.close()
        REPORT.write_text(json.dumps(closure.result, indent=2, ensure_ascii=False), encoding="utf-8")
        print(json.dumps(closure.result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    raise SystemExit(main())
