#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path

BASE_PATH = Path(__file__).with_name("staging_sprint_8c_browser_mobile.py")
spec = importlib.util.spec_from_file_location("sellora_sprint_8c_browser_mobile", BASE_PATH)
if spec is None or spec.loader is None:
    raise SystemExit("Unable to load Sprint 8C browser runner")
base = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = base
spec.loader.exec_module(base)


class BrowserClosureV2(base.Closure):
    def __init__(self) -> None:
        super().__init__()
        self.workspace_a_name = ""

    def resolve_workspace_b(self) -> None:
        response = self.api.get(f"{base.API}/api/v1/workspaces", headers=self.headers(base.WORKSPACE_A))
        self.check("Isolation", "workspace list available", response.status_code == 200, base.response_detail(response))
        if response.status_code != 200:
            raise RuntimeError("Workspace list unavailable")
        workspaces = response.json()
        workspace_a = next((item for item in workspaces if str(item.get("id")) == base.WORKSPACE_A), None)
        if not workspace_a:
            raise RuntimeError("Workspace A is not available to OWNER")
        self.workspace_a_name = str(workspace_a.get("name") or "")
        candidates = [
            item for item in workspaces
            if str(item.get("id")) != base.WORKSPACE_A
            and item.get("is_active") is True
            and ("QA" in str(item.get("name")) or "Sprint 8C" in str(item.get("name")))
        ]
        if not candidates:
            raise RuntimeError("No active synthetic Workspace B membership available")
        chosen = candidates[0]
        self.workspace_b_id = str(chosen["id"])
        self.workspace_b_name = str(chosen["name"])
        self.check("Isolation", "Workspace A and B resolved", bool(self.workspace_a_name and self.workspace_b_id))

    def invalid_csv(self, suffix: str) -> bytes:
        return (
            "Name,Instagram\n"
            f"=CMD,qa8c_invalid_{suffix}\n"
        ).encode("utf-8")

    def functional_flow(self, browser) -> None:
        context = self.init_context(browser, 1366, 768, "light", delay_imports=True)
        page = context.new_page()
        evidence = self.watch(page, "functional/desktop/light")
        try:
            page.goto(f"{base.FRONTEND}/settings/import", wait_until="domcontentloaded", timeout=60000)
            self.wait_ready(page)
            self.check("Browser", "functional initial body overflow = 0", self.body_overflow_ok(page))
            file_input = page.locator('input[type="file"]')
            upload_button = file_input.locator("xpath=..//button").first
            with page.expect_response(
                lambda response: response.url.endswith("/api/v1/import/upload") and response.request.method == "POST",
                timeout=120000,
            ) as upload_info:
                file_input.set_input_files({
                    "name": "qa8c-browser-valid.csv",
                    "mimeType": "text/csv",
                    "buffer": self.valid_csv("functional"),
                })
                page.wait_for_timeout(250)
                self.check(
                    "Browser",
                    "upload loading state visible",
                    upload_button.is_disabled() and bool(re.search(r"завантаж|upload", upload_button.inner_text(), re.I)),
                )
            self.check("Browser", "valid upload HTTP 201", upload_info.value.status == 201, upload_info.value.status)
            self.select_csv_and_preview(page)
            self.set_mapping(page, {"name": "Name", "instagram_username": "Instagram"})

            validate = page.get_by_role("button", name=re.compile(r"валідац|перевір|validate", re.I)).first
            with page.expect_response(lambda response: "/validate" in response.url and response.request.method == "POST", timeout=120000) as validation_info:
                validate.click()
            self.check("Browser", "valid flow validation HTTP 200", validation_info.value.status == 200, validation_info.value.status)

            dry_response = self.click_dry_run(page)
            self.check("Browser", "valid flow dry-run HTTP 200", dry_response.status == 200, dry_response.status)
            page.locator("[data-import-dry-run-report]").wait_for(state="visible", timeout=30000)
            body_before = page.locator("body").inner_text()
            job_match = re.search(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", body_before, re.I)
            job_id = job_match.group(0) if job_match else ""
            self.check("Browser", "browser job ID visible", bool(job_id))

            trigger = page.locator("[data-import-execute-trigger]")
            self.check("Browser", "primary execute CTA visible", trigger.is_visible() and trigger.is_enabled())
            trigger.click()
            dialog = page.get_by_role("dialog")
            dialog.wait_for(state="visible", timeout=15000)
            self.check("Browser", "execute confirmation visible", dialog.is_visible())
            self.screenshot(page, "functional-execute-confirmation.png")
            confirm = dialog.get_by_role("button", name=re.compile(r"виконати імпорт|execute import", re.I)).first
            with page.expect_response(lambda response: "/execute" in response.url and response.request.method == "POST", timeout=180000) as execute_info:
                confirm.evaluate("element => { element.click(); element.click(); }")
                page.wait_for_timeout(250)
                self.check("Browser", "execute confirmation pending state", confirm.is_disabled())
            self.check("Browser", "valid execute HTTP 200", execute_info.value.status == 200, execute_info.value.status)
            page.wait_for_timeout(1200)
            self.check("Browser", "duplicate execute requests = 0", evidence.execute_posts == 1, evidence.execute_posts)
            self.check("Browser", "single upload request", evidence.upload_posts == 1, evidence.upload_posts)
            self.screenshot(page, "functional-result-report.png")

            self.switch_workspace(page, 1366, self.workspace_b_name, self.workspace_b_id)
            page.goto(f"{base.FRONTEND}/settings/import", wait_until="domcontentloaded", timeout=60000)
            self.wait_ready(page)
            body_b = page.locator("body").inner_text()
            self.check(
                "Isolation",
                "old frontend import state cleared in Workspace B",
                "qa8c-browser-valid.csv" not in body_b and (not job_id or job_id not in body_b),
            )
            self.switch_workspace(page, 1366, self.workspace_a_name, base.WORKSPACE_A)
            self.check(
                "Isolation",
                "workspace switch A-B-A completed",
                page.evaluate("localStorage.getItem('sellora.current_workspace_id')") == base.WORKSPACE_A,
            )
        except Exception as exc:
            self.check("Browser", "functional flow completed", False, str(exc)[:300])
        finally:
            self.assert_clean_runtime("Browser", evidence)
            context.close()

    def visual_matrix(self, browser) -> None:
        downloaded_error_csv = False
        for viewport_name, width, height in base.VIEWPORTS:
            for theme in base.THEMES:
                label = f"{viewport_name}/{theme}"
                context = self.init_context(browser, width, height, theme)
                page = context.new_page()
                evidence = self.watch(page, label)
                try:
                    page.goto(f"{base.FRONTEND}/settings/import", wait_until="domcontentloaded", timeout=60000)
                    self.wait_ready(page)
                    actual_theme = page.evaluate("document.documentElement.dataset.theme")
                    self.check("Visual", f"{label}: theme applied", actual_theme == theme, actual_theme)
                    self.check("Visual", f"{label}: initial body overflow = 0", self.body_overflow_ok(page))
                    suffix = re.sub(r"[^a-z0-9]", "", label.lower())
                    input_file = page.locator('input[type="file"]')
                    with page.expect_response(lambda response: response.url.endswith("/api/v1/import/upload") and response.request.method == "POST", timeout=120000) as upload_info:
                        input_file.set_input_files({
                            "name": f"qa8c-{suffix}.csv",
                            "mimeType": "text/csv",
                            "buffer": self.invalid_csv(suffix),
                        })
                    self.check("Visual", f"{label}: upload HTTP 201", upload_info.value.status == 201, upload_info.value.status)
                    self.select_csv_and_preview(page)
                    self.set_mapping(page, {"name": "Name", "instagram_username": "Instagram"})
                    self.check("Visual", f"{label}: preview table uses inner scroll", page.locator(".sellora-scrollbar").count() > 0)

                    validate = page.get_by_role("button", name=re.compile(r"валідац|перевір|validate", re.I)).first
                    with page.expect_response(lambda response: "/validate" in response.url and response.request.method == "POST", timeout=120000) as validation_info:
                        validate.click()
                    self.check("Visual", f"{label}: invalid validation HTTP 200", validation_info.value.status == 200, validation_info.value.status)
                    issues = page.locator("[data-import-validation-issues]")
                    issues.wait_for(state="visible", timeout=30000)
                    issue_text = issues.inner_text().strip()
                    self.check("Visual", f"{label}: localized long validation message visible", len(issue_text) > 20)

                    dry = self.click_dry_run(page)
                    self.check("Visual", f"{label}: invalid dry-run HTTP 200", dry.status == 200, dry.status)
                    page.locator("[data-import-dry-run-report]").wait_for(state="visible", timeout=30000)
                    download_link = page.locator("[data-import-error-csv-download]")
                    self.check("Visual", f"{label}: error CSV download visible", download_link.count() == 1 and download_link.is_visible())
                    if not downloaded_error_csv and download_link.count() == 1:
                        with page.expect_download(timeout=30000) as download_info:
                            download_link.click()
                        self.check("Visual", "error CSV download works", download_info.value.suggested_filename.endswith(".csv"), download_info.value.suggested_filename)
                        downloaded_error_csv = True
                    trigger = page.locator("[data-import-execute-trigger]")
                    self.check("Visual", f"{label}: primary CTA visible", trigger.is_visible())
                    self.check("Visual", f"{label}: execute unavailable for invalid file", trigger.is_disabled())
                    self.check("Visual", f"{label}: final body overflow = 0", self.body_overflow_ok(page))
                    self.check("Visual", f"{label}: duplicate upload requests = 0", evidence.upload_posts == 1, evidence.upload_posts)
                    self.screenshot(page, f"{viewport_name}-{theme}-invalid-dry-run.png")
                except Exception as exc:
                    self.check("Visual", f"{label}: scenario completed", False, str(exc)[:300])
                finally:
                    self.assert_clean_runtime("Visual", evidence)
                    context.close()


if __name__ == "__main__":
    base.OUT_DIR.mkdir(parents=True, exist_ok=True)
    closure = BrowserClosureV2()
    try:
        exit_code = closure.run()
    except Exception as exc:
        closure.result["safe_error"] = str(exc)[:400]
        exit_code = 1
    finally:
        closure.close()
        base.REPORT.write_text(json.dumps(closure.result, indent=2, ensure_ascii=False), encoding="utf-8")
        print(json.dumps(closure.result, indent=2, ensure_ascii=False))
    raise SystemExit(exit_code)
