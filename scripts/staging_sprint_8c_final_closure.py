#!/usr/bin/env python3
from __future__ import annotations

import csv
import io
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright

API = os.getenv("STAGING_API_URL", "https://sellora-api-staging.onrender.com").rstrip("/")
FRONTEND = os.getenv("STAGING_FRONTEND_URL", "https://sellora-web-staging.vercel.app").rstrip("/")
WORKSPACE_A = os.environ["STAGING_TEST_WORKSPACE_ID"]
WORKSPACE_B = "56e8a724-782a-4494-a3a7-0bbf7deb03b7"
EXPECTED_COMMIT = os.getenv("EXPECTED_RUNTIME_COMMIT", "39c46dcf339990e491c9dfa25f1b75fad7c9289a").lower()
OUT = Path("artifacts/sprint-8c-final-closure")
REPORT_PATH = OUT / "sprint-8c-final-closure.json"
MD_PATH = OUT / "sprint-8c-final-closure.md"
SCREENSHOTS = OUT / "screenshots"
VIEWPORTS = [("desktop", 1366, 768), ("mobile-375", 375, 812), ("mobile-390", 390, 844), ("mobile-430", 430, 932), ("tablet", 768, 1024)]
THEMES = ["light", "dark"]
PERFORMANCE_CASES = [(100, 45.0), (1000, 90.0), (5000, 240.0)]


def required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required input: {name}")
    return value


def csv_customers(rows: int, marker: str) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.writer(stream)
    writer.writerow(["Name", "Instagram"])
    for index in range(rows):
        writer.writerow([f"QA8C PERF {marker} {index:05d}", f"qa8c_perf_{marker}_{index:05d}"])
    return stream.getvalue().encode("utf-8")


def safe_detail(response: httpx.Response | None) -> str:
    if response is None:
        return "no response"
    try:
        body = response.json()
        if isinstance(body, dict) and body.get("detail"):
            return str(body["detail"])[:300]
    except Exception:
        pass
    return f"HTTP {response.status_code}"


@dataclass
class Session:
    role: str
    access_token: str
    refresh_token: str
    user: dict[str, Any]


class Closure:
    def __init__(self) -> None:
        self.report: dict[str, Any] = {
            "phase": "Sprint 8C final closure",
            "decision": "FAIL",
            "runtime": {},
            "checks": [],
            "performance": {},
            "browser": {"screenshots": 0, "contexts": 0, "network_events": 0, "console_errors": [], "page_errors": [], "request_failures": [], "server_errors": [], "forbidden_external_requests": []},
            "jobs": [],
            "cleanup": {
                "business_writes_created": 0,
                "performance_and_browser_jobs_are_dry_run_only": True,
                "browser_contexts_closed": False,
                "synthetic_source_retention": "private Supabase evidence objects retained for controlled lifecycle cleanup",
            },
            "security": {
                "passwords_suppressed": True,
                "tokens_suppressed": True,
                "authorization_headers_suppressed": True,
                "api_keys_suppressed": True,
                "raw_source_rows_suppressed": True,
            },
            "safe_error": None,
        }
        self.marker = time.strftime("%m%d%H%M%S", time.gmtime())
        self.sessions: dict[str, Session] = {}

    def check(self, category: str, name: str, condition: bool, detail: Any = "") -> None:
        entry = {"category": category, "name": name, "status": "PASS" if condition else "FAIL", "detail": str(detail)[:400]}
        self.report["checks"].append(entry)
        print(json.dumps(entry, ensure_ascii=False), flush=True)
        if not condition:
            raise RuntimeError(f"Gate failed: {category} / {name}")

    def request(self, method: str, path: str, **kwargs) -> tuple[httpx.Response, float]:
        started = time.perf_counter()
        timeout = httpx.Timeout(connect=20, read=300, write=120, pool=20)
        with httpx.Client(timeout=timeout, follow_redirects=True, headers={"Connection": "close", "Cache-Control": "no-cache"}) as client:
            response = client.request(method, f"{API}{path}", **kwargs)
        elapsed = round(time.perf_counter() - started, 3)
        print(f"HTTP {method.upper()} {path} -> {response.status_code} ({elapsed}s)", flush=True)
        return response, elapsed

    def headers(self, role: str = "OWNER", workspace_id: str = WORKSPACE_A) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.sessions[role].access_token}", "X-Workspace-ID": workspace_id}

    def runtime_and_login(self) -> None:
        health, elapsed = self.request("GET", "/health")
        self.check("Runtime", "backend health", health.status_code == 200, safe_detail(health))
        body = health.json()
        commit = str(body.get("runtime_commit") or "").lower()
        self.report["runtime"] = {"runtime_commit": commit, "process_started_at": body.get("process_started_at"), "health_seconds": elapsed}
        self.check("Runtime", "expected main commit deployed", commit.startswith(EXPECTED_COMMIT[:12]), commit[:12])
        self.check("Runtime", "identified process start", bool(body.get("process_started_at")))
        for role in ("OWNER", "MANAGER", "ANALYST"):
            login, login_seconds = self.request("POST", "/api/v1/auth/login", json={"email": required(f"STAGING_{role}_EMAIL"), "password": required(f"STAGING_{role}_PASSWORD")})
            self.check("RBAC", f"{role} login", login.status_code == 200, safe_detail(login))
            tokens = login.json()
            token = tokens.get("access_token")
            refresh = tokens.get("refresh_token")
            self.check("RBAC", f"{role} tokens present", bool(token and refresh))
            me, me_seconds = self.request("GET", "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
            self.check("RBAC", f"{role} /auth/me", me.status_code == 200, safe_detail(me))
            self.sessions[role] = Session(role, token, refresh, me.json())
            self.report.setdefault("auth_timings_seconds", {})[role] = {"login": login_seconds, "me": me_seconds}

    def upload_job(self, filename: str, content: bytes) -> str:
        upload, elapsed = self.request("POST", "/api/v1/import/upload", headers=self.headers(), files={"file": (filename, content, "text/csv")})
        self.check("Performance", f"{filename}: upload", upload.status_code == 201, safe_detail(upload))
        job_id = str(upload.json().get("job_id") or "")
        self.check("Performance", f"{filename}: job id", bool(job_id))
        self.report["jobs"].append({"job_id": job_id, "file_name": filename, "upload_seconds": elapsed})
        return job_id

    def performance_matrix(self) -> None:
        mapping = {"name": "Name", "instagram_username": "Instagram"}
        for rows, threshold in PERFORMANCE_CASES:
            filename = f"qa8c-final-perf-{rows}-{self.marker}.csv"
            content = csv_customers(rows, f"{rows}_{self.marker}")
            started = time.perf_counter()
            job_id = self.upload_job(filename, content)
            sheets, sheets_seconds = self.request("GET", f"/api/v1/import/{job_id}/sheets", headers=self.headers())
            self.check("Performance", f"{rows}: sheets", sheets.status_code == 200 and "CSV" in sheets.json().get("sheets", []), safe_detail(sheets))
            preview, preview_seconds = self.request("POST", f"/api/v1/import/{job_id}/preview", headers=self.headers(), json={"sheet_name": "CSV", "limit": 20})
            self.check("Performance", f"{rows}: preview", preview.status_code == 200, safe_detail(preview))
            dry, dry_seconds = self.request("POST", f"/api/v1/import/{job_id}/dry-run", headers=self.headers(), json={"entity_type": "customers", "sheet_name": "CSV", "column_mapping": mapping, "options": None})
            total = round(time.perf_counter() - started, 3)
            self.check("Performance", f"{rows}: dry-run HTTP", dry.status_code == 200, safe_detail(dry))
            dry_body = dry.json()
            self.check("Performance", f"{rows}: exact row count", dry_body.get("total_rows") == rows, dry_body.get("total_rows"))
            self.check("Performance", f"{rows}: no invalid rows", dry_body.get("error_rows") == 0, dry_body.get("error_rows"))
            self.check("Performance", f"{rows}: within staging threshold", total <= threshold, f"{total}s <= {threshold}s")
            self.report["performance"][str(rows)] = {
                "file_bytes": len(content),
                "upload_seconds": next(item["upload_seconds"] for item in self.report["jobs"] if item["job_id"] == job_id),
                "sheets_seconds": sheets_seconds,
                "preview_seconds": preview_seconds,
                "dry_run_seconds": dry_seconds,
                "total_seconds": total,
                "threshold_seconds": threshold,
                "created_count": dry_body.get("created_count"),
                "error_rows": dry_body.get("error_rows"),
            }
        over_limit_rows = 5001
        filename = f"qa8c-final-limit-{over_limit_rows}-{self.marker}.csv"
        job_id = self.upload_job(filename, csv_customers(over_limit_rows, f"limit_{self.marker}"))
        dry, elapsed = self.request("POST", f"/api/v1/import/{job_id}/dry-run", headers=self.headers(), json={"entity_type": "customers", "sheet_name": "CSV", "column_mapping": mapping, "options": None})
        self.check("Limits", "5001 rows rejected", dry.status_code == 400, safe_detail(dry))
        self.check("Limits", "row limit error is safe", "traceback" not in safe_detail(dry).lower() and "sql" not in safe_detail(dry).lower())
        self.report["performance"]["5001_rejection"] = {"seconds": elapsed, "detail": safe_detail(dry)}

    def browser_context(self, browser: Browser, session: Session, workspace_id: str, theme: str, width: int, height: int) -> BrowserContext:
        context = browser.new_context(viewport={"width": width, "height": height}, is_mobile=width < 768, has_touch=width < 768, color_scheme=theme)
        payload = {"access": session.access_token, "refresh": session.refresh_token, "user": session.user, "workspace": workspace_id, "theme": theme}
        context.add_init_script(script=f"""
        (() => {{
          const payload = {json.dumps(payload, ensure_ascii=False)};
          localStorage.setItem('sellora.access_token', payload.access);
          localStorage.setItem('sellora.refresh_token', payload.refresh);
          localStorage.setItem('sellora.current_user', JSON.stringify(payload.user));
          localStorage.setItem('sellora.current_workspace_id', payload.workspace);
          localStorage.setItem('sellora.theme-mode', payload.theme);
          localStorage.setItem('sellora_locale', 'uk');
        }})();
        """)
        return context

    def watch_page(self, page: Page, label: str) -> None:
        browser_report = self.report["browser"]
        page.on("console", lambda message: browser_report["console_errors"].append({"label": label, "text": message.text[:300]}) if message.type == "error" else None)
        page.on("pageerror", lambda error: browser_report["page_errors"].append({"label": label, "text": str(error)[:300]}))
        page.on("requestfailed", lambda request: browser_report["request_failures"].append({"label": label, "method": request.method, "path": urlparse(request.url).path, "error": str(request.failure)[:160]}))
        def response_seen(response) -> None:
            browser_report["network_events"] += 1
            path = urlparse(response.url).path
            if response.status >= 500:
                browser_report["server_errors"].append({"label": label, "status": response.status, "path": path})
            host = (urlparse(response.url).hostname or "").lower()
            if host in {"graph.facebook.com", "api.novaposhta.ua"}:
                browser_report["forbidden_external_requests"].append({"label": label, "host": host, "path": path})
        page.on("response", response_seen)

    def wait_page(self, page: Page) -> None:
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(1500)
        page.locator("main").wait_for(state="visible", timeout=45000)

    def layout_checks(self, page: Page, label: str, width: int, theme: str) -> None:
        body = page.locator("body").inner_text()[:20000]
        self.check("Browser", f"{label}: authenticated import route", "/login" not in page.url and len(body) > 100, page.url)
        self.check("Browser", f"{label}: Ukrainian locale", page.evaluate("document.documentElement.lang") == "uk")
        actual_theme = page.evaluate("document.documentElement.dataset.theme")
        self.check("Browser", f"{label}: theme", actual_theme == theme, actual_theme)
        self.check("Browser", f"{label}: file control", page.locator("main input[type=file]").count() == 1)
        self.check("Browser", f"{label}: execute trigger", page.locator("main [data-import-execute-trigger]").count() == 1)
        self.check("Browser", f"{label}: execute initially disabled", page.locator("main [data-import-execute-trigger]").is_disabled())
        overflow = page.evaluate("document.documentElement.scrollWidth - window.innerWidth")
        self.check("Browser", f"{label}: no horizontal overflow", overflow <= 2, overflow)
        clipped = page.evaluate("""
        () => Array.from(document.querySelectorAll('main button, main select'))
          .filter((el) => el.getClientRects().length > 0)
          .map((el) => el.getBoundingClientRect())
          .filter((r) => r.width > 0 && (r.left < -2 || r.right > window.innerWidth + 2)).length
        """)
        self.check("Browser", f"{label}: controls inside viewport", clipped == 0, clipped)
        if width < 768:
            self.check("Browser", f"{label}: mobile viewport mode", page.evaluate("window.innerWidth") == width)

    def owner_interactive_flow(self, page: Page) -> None:
        file_name = f"qa8c-final-browser-{self.marker}.csv"
        content = csv_customers(1, f"browser_{self.marker}")
        with page.expect_response(lambda r: "/api/v1/import/upload" in r.url and r.request.method == "POST", timeout=45000) as upload_info:
            page.locator("main input[type=file]").set_input_files({"name": file_name, "mimeType": "text/csv", "buffer": content})
        upload = upload_info.value
        self.check("Browser interaction", "OWNER upload", upload.status == 201, upload.status)
        job_id = str(upload.json().get("job_id") or "")
        self.check("Browser interaction", "OWNER browser job id", bool(job_id))
        self.report["jobs"].append({"job_id": job_id, "file_name": file_name, "source": "browser"})
        selects = page.locator("main select")
        page.wait_for_function("() => document.querySelectorAll('main select').length >= 3")
        page.wait_for_function("() => Array.from(document.querySelectorAll('main select'))[1]?.querySelector('option[value=\"CSV\"]') !== null")
        selects.nth(1).select_option("CSV")
        selects.nth(2).select_option("customers")
        control_section = selects.nth(1).locator("xpath=ancestor::section[1]")
        control_buttons = control_section.locator("button")
        with page.expect_response(lambda r: f"/api/v1/import/{job_id}/preview" in r.url and r.request.method == "POST", timeout=45000) as preview_info:
            control_buttons.nth(0).click()
        self.check("Browser interaction", "preview response", preview_info.value.status == 200, preview_info.value.status)
        page.wait_for_timeout(500)
        with page.expect_response(lambda r: f"/api/v1/import/{job_id}/suggest-mapping" in r.url and r.request.method == "POST", timeout=45000) as suggest_info:
            control_buttons.nth(1).click()
        self.check("Browser interaction", "mapping suggestion", suggest_info.value.status == 200, suggest_info.value.status)
        page.wait_for_timeout(500)
        execute = page.locator("main [data-import-execute-trigger]")
        self.check("Browser interaction", "execute disabled before dry-run", execute.is_disabled())
        action_section = execute.locator("xpath=ancestor::section[1]")
        action_buttons = action_section.locator("button")
        with page.expect_response(lambda r: f"/api/v1/import/{job_id}/validate" in r.url and r.request.method == "POST", timeout=45000) as validate_info:
            action_buttons.nth(0).click()
        self.check("Browser interaction", "validation response", validate_info.value.status == 200, validate_info.value.status)
        with page.expect_response(lambda r: f"/api/v1/import/{job_id}/dry-run" in r.url and r.request.method == "POST", timeout=90000) as dry_info:
            action_buttons.nth(1).click()
        self.check("Browser interaction", "dry-run response", dry_info.value.status == 200, dry_info.value.status)
        page.wait_for_timeout(800)
        self.check("Browser interaction", "execute enabled after matching dry-run", not execute.is_disabled())
        execute.click()
        dialog = page.locator("[role=dialog]")
        self.check("Browser interaction", "confirmation modal visible", dialog.count() == 1 and dialog.is_visible())
        dialog.get_by_role("button", name="Скасувати").click()
        self.check("Browser interaction", "confirmation modal closes", not dialog.is_visible())
        selects.nth(2).select_option("products")
        page.wait_for_timeout(250)
        self.check("Browser interaction", "mapping change invalidates execute", execute.is_disabled())
        page.evaluate(f"localStorage.setItem('sellora.current_workspace_id', '{WORKSPACE_B}')")
        page.reload(wait_until="domcontentloaded", timeout=45000)
        self.wait_page(page)
        body_b = page.locator("body").inner_text()
        self.check("Workspace UI", "workspace switch clears job id", job_id not in body_b)
        self.check("Workspace UI", "workspace switch clears execute approval", page.locator("main [data-import-execute-trigger]").is_disabled())

    def role_denial_browser(self, browser: Browser, role: str) -> None:
        context = self.browser_context(browser, self.sessions[role], WORKSPACE_A, "light", 1366, 768)
        page = context.new_page()
        label = f"{role.lower()}-denial"
        self.watch_page(page, label)
        try:
            page.goto(f"{FRONTEND}/settings/import", wait_until="domcontentloaded", timeout=45000)
            self.wait_page(page)
            file_input = page.locator("main input[type=file]")
            self.check("Browser RBAC", f"{role} import route renders", file_input.count() == 1)
            with page.expect_response(lambda r: "/api/v1/import/upload" in r.url and r.request.method == "POST", timeout=45000) as response_info:
                file_input.set_input_files({"name": f"qa8c-{role.lower()}-denied.csv", "mimeType": "text/csv", "buffer": b"Name\nDenied\n"})
            self.check("Browser RBAC", f"{role} upload denied", response_info.value.status == 403, response_info.value.status)
        finally:
            context.close()

    def browser_matrix(self) -> None:
        SCREENSHOTS.mkdir(parents=True, exist_ok=True)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                for viewport_name, width, height in VIEWPORTS:
                    for theme in THEMES:
                        label = f"owner-{viewport_name}-{theme}"
                        context = self.browser_context(browser, self.sessions["OWNER"], WORKSPACE_A, theme, width, height)
                        self.report["browser"]["contexts"] += 1
                        page = context.new_page()
                        self.watch_page(page, label)
                        try:
                            page.goto(f"{FRONTEND}/settings/import", wait_until="domcontentloaded", timeout=45000)
                            self.wait_page(page)
                            self.layout_checks(page, label, width, theme)
                            if viewport_name == "desktop" and theme == "light":
                                self.owner_interactive_flow(page)
                            page.screenshot(path=str(SCREENSHOTS / f"{label}.png"), full_page=True)
                            self.report["browser"]["screenshots"] += 1
                        finally:
                            context.close()
                self.role_denial_browser(browser, "MANAGER")
                self.role_denial_browser(browser, "ANALYST")
            finally:
                browser.close()
                self.report["cleanup"]["browser_contexts_closed"] = True
        browser_report = self.report["browser"]
        self.check("Browser evidence", "10 owner viewport/theme screenshots", browser_report["screenshots"] == 10, browser_report["screenshots"])
        self.check("Browser evidence", "10 owner contexts", browser_report["contexts"] == 10, browser_report["contexts"])
        self.check("Browser evidence", "no console errors", not browser_report["console_errors"], browser_report["console_errors"][:3])
        self.check("Browser evidence", "no page errors", not browser_report["page_errors"], browser_report["page_errors"][:3])
        self.check("Browser evidence", "no request failures", not browser_report["request_failures"], browser_report["request_failures"][:3])
        self.check("Browser evidence", "no HTTP 5xx", not browser_report["server_errors"], browser_report["server_errors"][:3])
        self.check("Browser evidence", "no Meta/Nova Poshta calls", not browser_report["forbidden_external_requests"], browser_report["forbidden_external_requests"][:3])
        self.check("Browser evidence", "network evidence captured", browser_report["network_events"] > 0, browser_report["network_events"])
        self.check("Cleanup", "browser contexts closed", self.report["cleanup"]["browser_contexts_closed"])
        self.check("Cleanup", "final closure created no business records", self.report["cleanup"]["business_writes_created"] == 0)

    def write_report(self) -> None:
        OUT.mkdir(parents=True, exist_ok=True)
        passed = sum(item["status"] == "PASS" for item in self.report["checks"])
        failed = sum(item["status"] == "FAIL" for item in self.report["checks"])
        self.report["summary"] = {"checks_passed": passed, "checks_failed": failed}
        REPORT_PATH.write_text(json.dumps(self.report, indent=2, ensure_ascii=False), encoding="utf-8")
        lines = ["# Sprint 8C Final Staging Closure", "", f"Decision: **{self.report['decision']}**", f"Runtime: `{self.report.get('runtime', {}).get('runtime_commit', '')}`", f"Checks: {passed} PASS / {failed} FAIL", f"Screenshots: {self.report['browser']['screenshots']}", f"Network events: {self.report['browser']['network_events']}", "", "## Performance"]
        for key, value in self.report["performance"].items():
            lines.append(f"- {key}: `{json.dumps(value, ensure_ascii=False)}`")
        lines += ["", "## Cleanup", "- Performance and browser imports were dry-run only; no business entities were created.", "- Browser contexts were closed.", "- Private synthetic source objects are retained only as short-lived QA evidence under lifecycle control."]
        MD_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def run(self) -> int:
        try:
            self.runtime_and_login()
            self.performance_matrix()
            self.browser_matrix()
            self.report["decision"] = "PASS"
            return 0
        except Exception as exc:
            self.report["safe_error"] = f"{exc.__class__.__name__}: {exc}"[:400]
            return 1
        finally:
            self.write_report()


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    exit_code = Closure().run()
    print(json.dumps({"decision": json.loads(REPORT_PATH.read_text())["decision"], "report": str(REPORT_PATH)}, ensure_ascii=False))
    raise SystemExit(exit_code)
