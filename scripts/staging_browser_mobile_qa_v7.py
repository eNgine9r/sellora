#!/usr/bin/env python3
"""Final Step 8 QA assertions for synthetic email visibility and logout."""
from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

MODULE_PATH = Path(__file__).with_name("staging_browser_mobile_qa_v6.py")
spec = importlib.util.spec_from_file_location("sellora_browser_qa_v6", MODULE_PATH)
if spec is None or spec.loader is None:
    raise SystemExit("Unable to load browser QA v6 module")
v6 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v6)


class ApprovedBrowserQa(v6.FinalBrowserQa):
    def has_secret_value(self, text: str) -> bool:
        # Synthetic account email is expected to be visible on Team/Profile pages.
        # Passwords, access tokens and API-key/JWT patterns remain forbidden.
        sensitive_values = [value for value in (self.password, self.access_token) if value]
        if any(value in text for value in sensitive_values):
            return True
        return any(pattern.search(text) for pattern in v6.v5.v4.module.TOKEN_PATTERNS)

    def logout(self, page, viewport: str, width: int) -> None:
        self.open_workspace_menu(page, width)
        label = re.compile(r"^(Вийти|Logout|Sign out)$", re.I)

        target = page.get_by_role("menuitem", name=label)
        if target.count() == 0:
            target = page.get_by_role("button", name=label)
        if target.count() == 0:
            target = page.locator("button:visible").filter(has_text=label)
        if target.count() == 0:
            self.finding("FAIL", viewport, "Logout", "logout_control", "Visible logout control not found")
            self.results.append({"viewport": viewport, "scenario": "Logout", "status": "FAIL", "path": "/login"})
            return

        target.first.click(timeout=15000)

        session_cleared = False
        redirected = False
        try:
            page.wait_for_function(
                "!localStorage.getItem('sellora.access_token') && !localStorage.getItem('sellora.refresh_token')",
                timeout=30000,
            )
            session_cleared = True
        except Exception:
            session_cleared = False

        try:
            page.wait_for_url(re.compile(r"/login(?:\?.*)?$"), timeout=30000)
            redirected = True
        except Exception:
            redirected = "/login" in page.url

        if not session_cleared or not redirected:
            self.finding(
                "FAIL",
                viewport,
                "Logout",
                "auth",
                f"Logout incomplete: session_cleared={session_cleared}, redirected={redirected}",
            )

        self.results.append({
            "viewport": viewport,
            "scenario": "Logout",
            "status": "PASS" if session_cleared and redirected else "FAIL",
            "path": "/login",
        })


if __name__ == "__main__":
    required = [
        "STAGING_FRONTEND_URL",
        "STAGING_API_URL",
        "STAGING_OWNER_EMAIL",
        "STAGING_OWNER_PASSWORD",
        "STAGING_TEST_WORKSPACE_ID",
        "STAGING_SECOND_WORKSPACE_ID",
    ]
    missing = [name for name in required if not v6.v5.v4.module.env(name)]
    if missing:
        print("Missing required browser QA inputs", file=sys.stderr)
        raise SystemExit(2)
    decision = ApprovedBrowserQa().run()
    print(f"Browser/mobile QA decision: {decision}")
    raise SystemExit(0 if decision == "PASS" else 1)
