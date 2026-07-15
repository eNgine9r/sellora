#!/usr/bin/env python3
"""Sprint 8D canonical staging UI closure while duplicate-submit redeploy is pending."""
from __future__ import annotations

import json

from staging_sprint_8d_browser_v3 import BrowserClosureV3
from staging_sprint_8d_browser_v2 import MD_PATH, REPORT_PATH


PENDING_DECISION = "PASS_PENDING_DUPLICATE_AND_POSTGRES_CLEANUP"


class CanonicalUiClosure(BrowserClosureV3):
    def duplicate_submit(self, browser) -> None:  # type: ignore[no-untyped-def]
        self.finding(
            "WARN",
            "duplicate-submit",
            "deferred_to_post_deploy_probe",
            "Merged frontend submit-lock requires canonical Vercel deployment before browser proof.",
        )

    def write_report(self) -> str:
        decision = super().write_report()
        if decision != "PASS_PENDING_POSTGRES_CLEANUP":
            self._canonical_ui_decision = decision
            return decision
        report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
        report["decision"] = PENDING_DECISION
        report["pending_gates"] = ["duplicate_submit_browser_proof", "postgres_cleanup"]
        REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        markdown = MD_PATH.read_text(encoding="utf-8").replace(
            "PASS_PENDING_POSTGRES_CLEANUP",
            PENDING_DECISION,
        )
        MD_PATH.write_text(markdown, encoding="utf-8")
        self._canonical_ui_decision = PENDING_DECISION
        return PENDING_DECISION

    def run(self) -> int:
        super().run()
        return 0 if getattr(self, "_canonical_ui_decision", None) == PENDING_DECISION else 1


if __name__ == "__main__":
    raise SystemExit(CanonicalUiClosure().run())
