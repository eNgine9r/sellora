#!/usr/bin/env python3
"""Narrow Sprint 8D mobile/desktop workspace-switch evidence after canonical UI matrix."""
from __future__ import annotations

import re

from staging_sprint_8d_browser_v4 import CanonicalUiClosure


class WorkspaceSwitchProbe(CanonicalUiClosure):
    def matrix(self, browser) -> None:  # type: ignore[no-untyped-def]
        self.finding("WARN", "matrix", "reused_prior_canonical_matrix", "Canonical 5×2 route/theme matrix is preserved in the preceding sanitized artifact.")

    def loading_states(self, browser) -> None:  # type: ignore[no-untyped-def]
        self.finding("WARN", "loading", "reused_prior_loading_evidence", "Orders, Inventory and Shipments loading states already passed in the canonical artifact.")

    def open_workspace_menu(self, page, width: int, programmatic: bool = False):  # type: ignore[no-untyped-def]
        trigger = (
            page.locator(".account-profile-trigger")
            if width >= 768
            else page.locator('[aria-controls="mobile-more-sheet"]')
        )
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


if __name__ == "__main__":
    raise SystemExit(WorkspaceSwitchProbe().run())
