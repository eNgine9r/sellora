#!/usr/bin/env python3
"""Cold-start tolerant and screenshot-safe browser/mobile QA entrypoint."""
from __future__ import annotations

import importlib.util
import re
import sys
import time
from pathlib import Path

MODULE_PATH = Path(__file__).with_name("staging_browser_mobile_qa_v4.py")
spec = importlib.util.spec_from_file_location("sellora_browser_qa_v4", MODULE_PATH)
if spec is None or spec.loader is None:
    raise SystemExit("Unable to load browser QA v4 module")
v4 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v4)


class ColdStartTolerantQa(v4.BrowserNativeQa):
    def login(self, page, viewport: str, width: int) -> bool:
        page.goto(f"{self.frontend}/login", wait_until="domcontentloaded", timeout=45000)
        self.wait(page)
        page.screenshot(path=str(v4.module.SHOTS / f"{viewport}-login.png"))

        email_input = page.locator('input[type="email"], input[autocomplete="email"]').first
        password_input = page.locator('input[type="password"], input[autocomplete="current-password"]').first
        email_input.fill(self.email)
        password_input.fill(self.password)
        page.locator('button[type="submit"]').first.click()

        deadline = time.monotonic() + 150
        token_present = False
        while time.monotonic() < deadline:
            try:
                token_present = bool(page.evaluate("Boolean(localStorage.getItem('sellora.access_token') && localStorage.getItem('sellora.refresh_token'))"))
            except Exception:
                token_present = False
            if token_present:
                break
            page.wait_for_timeout(2000)

        if not token_present:
            body = page.locator("body").inner_text(timeout=10000)
            feedback = "login request did not complete"
            for pattern in (
                r"невірн|invalid credential|неправильн",
                r"мереж|network|недоступ",
                r"помил|error",
            ):
                match = re.search(pattern, body, flags=re.I)
                if match:
                    feedback = f"visible feedback category: {match.group(0)}"
                    break
            self.finding("FAIL", viewport, "Login", "auth", f"Login timeout after 150s; {feedback}")
            return False

        if "/login" in page.url:
            page.goto(f"{self.frontend}/dashboard", wait_until="domcontentloaded", timeout=45000)
        self.wait(page)
        if "/login" in page.url:
            self.finding("FAIL", viewport, "Login", "auth", "Session token exists but protected route redirects to /login")
            return False

        self.switch_workspace_ui(page, viewport, width, self.workspace_a_name, self.workspace_a)
        if "/login" in page.url:
            return False
        self.results.append({"viewport": viewport, "scenario": "Login", "status": "PASS", "path": "/login"})
        return True

    def clear_sensitive_form_fields(self, page) -> None:
        try:
            page.locator('input[type="email"], input[autocomplete="email"]').evaluate_all(
                "elements => elements.forEach(element => { element.value = ''; element.setAttribute('value', ''); })"
            )
            page.locator('input[type="password"], input[autocomplete="current-password"]').evaluate_all(
                "elements => elements.forEach(element => { element.value = ''; element.setAttribute('value', ''); })"
            )
        except Exception:
            pass

    def run_viewport(self, browser, viewport: str, width: int, height: int) -> None:
        context = browser.new_context(
            viewport={"width": width, "height": height},
            is_mobile=width < 768,
            has_touch=width < 768,
        )
        page = context.new_page()
        self.watch(page, viewport)
        try:
            if not self.login(page, viewport, width):
                return
            self.prepare_fixtures_browser(page)
            self.verify_workspace_isolation(page, viewport, width)
            for scenario, path in v4.module.SCENARIOS:
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
            self.clear_sensitive_form_fields(page)
            try:
                page.screenshot(path=str(v4.module.SHOTS / f"{viewport}-runner-exception.png"), full_page=True)
            except Exception:
                pass
        finally:
            context.close()


if __name__ == "__main__":
    required = [
        "STAGING_FRONTEND_URL",
        "STAGING_OWNER_EMAIL",
        "STAGING_OWNER_PASSWORD",
        "STAGING_TEST_WORKSPACE_ID",
        "STAGING_SECOND_WORKSPACE_ID",
    ]
    missing = [name for name in required if not v4.module.env(name)]
    if missing:
        print("Missing required browser QA inputs", file=sys.stderr)
        raise SystemExit(2)
    decision = ColdStartTolerantQa().run()
    print(f"Browser/mobile QA decision: {decision}")
    raise SystemExit(0 if decision == "PASS" else 1)
