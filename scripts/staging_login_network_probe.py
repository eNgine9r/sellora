#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import TimeoutError, sync_playwright

OUT = Path("artifacts/login-network-probe")
REPORT = OUT / "login-network-probe.json"
FRONTEND = os.environ["STAGING_FRONTEND_URL"].rstrip("/")
EMAIL = os.environ["STAGING_OWNER_EMAIL"]
PASSWORD = os.environ["STAGING_OWNER_PASSWORD"]


def safe_url(url: str) -> dict[str, str]:
    parsed = urlparse(url)
    return {"scheme": parsed.scheme, "host": parsed.netloc, "path": parsed.path}


def redact(text: object) -> str:
    value = str(text).replace(EMAIL, "[REDACTED_EMAIL]").replace(PASSWORD, "[REDACTED_PASSWORD]")
    return value[:500]


OUT.mkdir(parents=True, exist_ok=True)
report: dict[str, object] = {
    "started_at": time.time(),
    "frontend": safe_url(FRONTEND),
    "auth_request": None,
    "auth_response": None,
    "auth_failure": None,
    "endpoint_reachability": None,
    "console_errors": [],
    "page_errors": [],
    "ui": {},
    "credentials_suppressed": True,
    "tokens_suppressed": True,
}

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context(viewport={"width": 1366, "height": 768}, locale="uk-UA", timezone_id="Europe/Kyiv")
    page = context.new_page()

    def on_request(request):
        if "/auth/login" in request.url:
            report["auth_request"] = {**safe_url(request.url), "method": request.method}

    def on_response(response):
        if "/auth/login" in response.url:
            report["auth_response"] = {**safe_url(response.url), "status": response.status}

    def on_failed(request):
        if "/auth/login" in request.url:
            report["auth_failure"] = {**safe_url(request.url), "error": redact(request.failure or "request failed")}

    page.on("request", on_request)
    page.on("response", on_response)
    page.on("requestfailed", on_failed)
    page.on("console", lambda message: report["console_errors"].append(redact(message.text)) if message.type == "error" else None)
    page.on("pageerror", lambda error: report["page_errors"].append(redact(error)))

    try:
        page.goto(f"{FRONTEND}/login", wait_until="domcontentloaded", timeout=45000)
        page.locator('input[type="email"]').fill(EMAIL)
        page.locator('input[type="password"]').fill(PASSWORD)
        page.get_by_role("button", name="Увійти", exact=True).click()

        deadline = time.monotonic() + 35
        while time.monotonic() < deadline:
            if report["auth_response"] or report["auth_failure"] or "/login" not in page.url:
                break
            page.wait_for_timeout(250)

        auth_request = report.get("auth_request")
        if isinstance(auth_request, dict):
            auth_url = f"{auth_request['scheme']}://{auth_request['host']}{auth_request['path']}"
            try:
                probe = context.request.get(auth_url, timeout=15000, fail_on_status_code=False)
                report["endpoint_reachability"] = {**safe_url(auth_url), "get_status": probe.status}
            except Exception as exc:
                report["endpoint_reachability"] = {**safe_url(auth_url), "error": redact(type(exc).__name__ + ": " + str(exc))}

        report["ui"] = {
            "current_path": urlparse(page.url).path,
            "submit_text": page.locator('button[type="submit"]').inner_text(timeout=5000),
            "access_token_present": page.evaluate("Boolean(localStorage.getItem('sellora.access_token'))"),
            "refresh_token_present": page.evaluate("Boolean(localStorage.getItem('sellora.refresh_token'))"),
            "visible_error": page.locator('[role="alert"], .text-red-600, .text-red-500').all_inner_texts(),
        }
    except Exception as exc:
        report["probe_exception"] = redact(type(exc).__name__ + ": " + str(exc))
    finally:
        report["finished_at"] = time.time()
        context.close()
        browser.close()

REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({
    "auth_request": report.get("auth_request"),
    "auth_response": report.get("auth_response"),
    "auth_failure": report.get("auth_failure"),
    "endpoint_reachability": report.get("endpoint_reachability"),
    "ui": report.get("ui"),
}, ensure_ascii=False))
