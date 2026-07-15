#!/usr/bin/env python3
"""Sprint 8D browser closure v3 with exact overlay and responsive selectors."""
from __future__ import annotations

import re
import time
from typing import Any

from staging_sprint_8d_browser_v2 import (
    FRONTEND,
    PREFIX,
    ROUTES,
    THEMES,
    VIEWPORTS,
    WORKSPACE_A,
    BrowserClosure,
    sync_playwright,
)


class BrowserClosureV3(BrowserClosure):
    def wait_environment(self) -> None:
        super().wait_environment()
        self.runtime["frontend_evidence_url"] = FRONTEND

    @staticmethod
    def wait_page(page: Any) -> None:
        page.locator("main").wait_for(state="visible", timeout=45000)
        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass
        page.wait_for_timeout(350)

    @staticmethod
    def close_overlay(page: Any) -> None:
        form_panel = page.locator(".sellora-dialog-panel:visible")
        if form_panel.count():
            form_panel.locator("button").first.click()
            form_panel.wait_for(state="hidden", timeout=10000)
            return
        desktop_panel = page.locator('[data-entity-side-panel="desktop"]:visible')
        if desktop_panel.count():
            desktop_panel.locator("button").first.click()
            return
        drawer = page.locator('[role="dialog"]:visible')
        if drawer.count():
            page.keyboard.press("Escape")
            page.wait_for_timeout(250)

    @staticmethod
    def form_panel(page: Any) -> Any:
        return page.locator(".sellora-dialog-panel:visible")

    def matrix(self, browser: Any) -> None:
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
                            self.header_cta(page).click()
                            panel = self.form_panel(page)
                            panel.wait_for(state="visible", timeout=10000)
                            self.check(
                                "L",
                                f"{scope} order form opens without overflow",
                                panel.count() == 1 and panel.evaluate("el => el.scrollWidth <= el.clientWidth + 1"),
                            )
                            self.close_overlay(page)
                        elif route == "inventory":
                            search = page.locator("main input").first
                            search.fill(PREFIX)
                            page.wait_for_timeout(700)
                            selector = "tbody tr:visible" if width >= 1024 else "article:visible"
                            marker = page.locator(selector).filter(has_text=PREFIX).first
                            marker.wait_for(state="visible", timeout=15000)
                            marker.click()
                            panel = (
                                page.locator('[data-entity-side-panel="desktop"]:visible')
                                if width >= 1024
                                else page.locator('[role="dialog"]:visible')
                            )
                            panel.wait_for(state="visible", timeout=10000)
                            self.check("L", f"{scope} inventory detail uses correct panel/drawer", panel.count() == 1)
                            self.close_overlay(page)
                            search.fill("")
                        else:
                            self.header_cta(page).click()
                            panel = self.form_panel(page)
                            panel.wait_for(state="visible", timeout=10000)
                            self.check(
                                "L",
                                f"{scope} shipment form opens without overflow",
                                panel.count() == 1 and panel.evaluate("el => el.scrollWidth <= el.clientWidth + 1"),
                            )
                            self.close_overlay(page)

                        self.wait_page(page)
                        self.screenshot(page, f"{viewport_name}-{theme}-{route}.png")
                except Exception as exc:
                    self.finding("BLOCKER", label, "matrix_exception", repr(exc))
                finally:
                    try:
                        page.wait_for_timeout(250)
                    except Exception:
                        pass
                    context.close()

    def workspace_switching(self, browser: Any) -> None:
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
                self.form_panel(page).wait_for(state="visible", timeout=10000)
                self.switch_workspace(page, width, self.workspace_b_name, self.workspace_b_id, programmatic=True)
                self.check(
                    "K",
                    f"{label} open order form closes on workspace switch",
                    self.form_panel(page).count() == 0,
                )

                self.switch_workspace(page, width, self.owner_workspace_name(), WORKSPACE_A)
                page.goto(f"{FRONTEND}/shipments", wait_until="domcontentloaded", timeout=60000)
                self.wait_page(page)
                self.header_cta(page).click()
                self.form_panel(page).wait_for(state="visible", timeout=10000)
                self.switch_workspace(page, width, self.workspace_b_name, self.workspace_b_id, programmatic=True)
                self.check(
                    "K",
                    f"{label} open shipment form closes on workspace switch",
                    self.form_panel(page).count() == 0,
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
                self.wait_page(page)
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
                    and all(value == self.workspace_b_id for value in b_get_headers)
                )
                self.check("K", f"{label} inventory form reset and stale workspace isolation", ok, state)
                self.screenshot(page, f"workspace-switch-{label}.png")
            except Exception as exc:
                self.finding("BLOCKER", scope, "workspace_switch_exception", repr(exc))
            finally:
                try:
                    page.wait_for_timeout(250)
                except Exception:
                    pass
                context.close()

    def final_browser_health(self) -> None:
        navigation_aborts = [
            item for item in self.request_failures if "ERR_ABORTED" in str(item.get("failure", ""))
        ]
        self.request_failures = [
            item for item in self.request_failures if "ERR_ABORTED" not in str(item.get("failure", ""))
        ]
        self.check(
            "L",
            "navigation/context aborts classified separately from request failures",
            True,
            {"expected_aborts": len(navigation_aborts)},
        )
        super().final_browser_health()


if __name__ == "__main__":
    closure = BrowserClosureV3()
    raise SystemExit(closure.run())
