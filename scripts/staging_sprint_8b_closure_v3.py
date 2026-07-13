#!/usr/bin/env python3
"""Evidence-rich Sprint 8B staging isolation closure runner."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

V2_PATH = Path(__file__).with_name("staging_sprint_8b_closure_v2.py")
spec = importlib.util.spec_from_file_location("sellora_sprint_8b_closure_v2", V2_PATH)
if spec is None or spec.loader is None:
    raise SystemExit("Unable to load Sprint 8B closure V2 module")
v2 = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = v2
spec.loader.exec_module(v2)
base = v2.base


def lead_names(value):
    if isinstance(value, list):
        return [str(item.get("name", "")) for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        for key in ("items", "results", "data"):
            if isinstance(value.get(key), list):
                return [str(item.get("name", "")) for item in value[key] if isinstance(item, dict)]
    return []


class Sprint8BClosureV3(v2.Sprint8BClosureV2):
    def init_context(self, browser, session, workspace_id, theme, width, height):
        context = browser.new_context(
            viewport={"width": width, "height": height},
            is_mobile=width < 768,
            has_touch=width < 768,
            color_scheme=theme,
        )
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
              const seedKey = 'sellora.qa-context-seeded';
              if (localStorage.getItem(seedKey) === 'true') return;
              const payload = {json.dumps(payload, ensure_ascii=False)};
              localStorage.setItem('sellora.access_token', payload.access);
              localStorage.setItem('sellora.refresh_token', payload.refresh);
              localStorage.setItem('sellora.current_user', JSON.stringify(payload.user));
              if (payload.workspace) localStorage.setItem('sellora.current_workspace_id', payload.workspace);
              else localStorage.removeItem('sellora.current_workspace_id');
              localStorage.setItem('sellora.theme-mode', payload.theme);
              localStorage.setItem(seedKey, 'true');
            }})();
            """
        )
        return context

    def demo_matrix_and_switch(self, browser) -> None:
        if not self.demo_workspace_id:
            return
        assert self.owner is not None
        self.create_real_marker()

        _, real_api_data = self.request(
            "GET",
            "/leads",
            token=self.owner.access_token,
            workspace_id=self.empty_workspace_id,
            expected=(200,),
        )
        real_api_names = lead_names(real_api_data)
        self.result(
            "Isolation",
            "real workspace API contains marker and no DEMO leads",
            self.real_marker in real_api_names and not any("DEMO Лід" in name for name in real_api_names),
            {"marker_present": self.real_marker in real_api_names, "demo_present": any("DEMO Лід" in name for name in real_api_names), "count": len(real_api_names)},
        )

        _, demo_api_data = self.request(
            "GET",
            "/leads",
            token=self.owner.access_token,
            workspace_id=self.demo_workspace_id,
            expected=(200,),
        )
        demo_api_names = lead_names(demo_api_data)
        self.result(
            "Isolation",
            "demo workspace API contains DEMO leads and no real marker",
            any("DEMO Лід" in name for name in demo_api_names) and self.real_marker not in demo_api_names,
            {"marker_present": self.real_marker in demo_api_names, "demo_present": any("DEMO Лід" in name for name in demo_api_names), "count": len(demo_api_names)},
        )

        for viewport_name, width, height in base.VIEWPORTS:
            for theme in base.THEMES:
                label = f"demo/{viewport_name}/{theme}"
                context = self.init_context(browser, self.owner, self.demo_workspace_id, theme, width, height)
                page = context.new_page()
                self.watch_page(page, label)
                try:
                    page.goto(f"{self.frontend}/dashboard", wait_until="domcontentloaded", timeout=45000)
                    self.wait_page(page)
                    banner = page.locator("[data-demo-workspace-banner]")
                    self.result(
                        "Demo UI",
                        f"{viewport_name}/{theme} banner and theme",
                        banner.count() == 1 and page.evaluate("document.documentElement.dataset.theme") == theme,
                    )
                    self.check_page(page, label, "demo dashboard", f"{label.replace('/', '-')}-dashboard.png")

                    for scenario, path in (
                        ("Shipments honest empty state", "/shipments"),
                        ("Advertising honest empty state", "/advertising"),
                        ("Finance truthful order-derived view", "/finance"),
                    ):
                        page.goto(f"{self.frontend}{path}", wait_until="domcontentloaded", timeout=45000)
                        self.check_page(page, label, scenario, f"{label.replace('/', '-')}-{path.strip('/').replace('/', '-')}.png")

                    self.switch_workspace(page, width, self.empty_workspace_name, self.empty_workspace_id)
                    with page.expect_response(
                        lambda response: "/api/v1/leads" in response.url and response.request.method == "GET",
                        timeout=45000,
                    ) as real_response_info:
                        page.goto(f"{self.frontend}/leads", wait_until="domcontentloaded", timeout=45000)
                    real_response = real_response_info.value
                    self.wait_page(page)
                    current_real_id = page.evaluate("localStorage.getItem('sellora.current_workspace_id')")
                    request_real_id = real_response.request.headers.get("x-workspace-id")
                    initial_real_body = page.locator("body").inner_text()[:20000]
                    stale_demo_before_search = "DEMO Лід" in initial_real_body
                    marker_visible = self.real_marker in initial_real_body

                    if not marker_visible:
                        search_input = page.locator("main input:visible").first
                        if search_input.count() > 0:
                            search_input.fill(self.real_marker)
                            page.wait_for_timeout(1200)
                            self.wait_page(page)
                    real_body = page.locator("body").inner_text()[:20000]
                    marker_visible = self.real_marker in real_body
                    demo_visible = "DEMO Лід" in real_body
                    real_ok = (
                        current_real_id == self.empty_workspace_id
                        and request_real_id == self.empty_workspace_id
                        and marker_visible
                        and not stale_demo_before_search
                        and not demo_visible
                    )
                    self.result(
                        "Isolation",
                        f"{viewport_name}/{theme} real workspace has no stale demo data",
                        real_ok,
                        {
                            "current_workspace_id": current_real_id,
                            "request_workspace_id": request_real_id,
                            "marker_visible": marker_visible,
                            "stale_demo_before_search": stale_demo_before_search,
                            "demo_visible_after_search": demo_visible,
                        },
                    )
                    self.check_page(
                        page,
                        label,
                        "real workspace marker and cache isolation",
                        f"{label.replace('/', '-')}-workspace-real.png",
                    )

                    self.switch_workspace(page, width, "Демо Sellora", self.demo_workspace_id)
                    page.goto(f"{self.frontend}/leads", wait_until="domcontentloaded", timeout=45000)
                    self.wait_page(page)
                    current_demo_id = page.evaluate("localStorage.getItem('sellora.current_workspace_id')")
                    demo_body = page.locator("body").inner_text()[:20000]
                    demo_ok = current_demo_id == self.demo_workspace_id and "DEMO Лід" in demo_body and self.real_marker not in demo_body
                    self.result(
                        "Isolation",
                        f"{viewport_name}/{theme} demo workspace has no stale real data",
                        demo_ok,
                        {
                            "current_workspace_id": current_demo_id,
                            "demo_visible": "DEMO Лід" in demo_body,
                            "real_marker_visible": self.real_marker in demo_body,
                        },
                    )
                    self.check_page(
                        page,
                        label,
                        "workspace switch real-demo-real cache isolation",
                        f"{label.replace('/', '-')}-workspace-switch.png",
                    )
                except Exception as exc:
                    self.finding("FAIL", label, "runner_exception", repr(exc))
                finally:
                    context.close()


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
    missing = [name for name in required if not base.env(name)]
    if missing:
        print("Missing required Sprint 8B staging inputs", file=sys.stderr)
        raise SystemExit(2)
    decision = Sprint8BClosureV3().run()
    print(f"Sprint 8B staging closure decision: {decision}")
    raise SystemExit(0 if decision == "PASS" else 1)
