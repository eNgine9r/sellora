#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

BASE_PATH = Path(__file__).with_name("staging_sprint_8c_final_closure.py")
spec = importlib.util.spec_from_file_location("sellora_sprint_8c_final_closure", BASE_PATH)
if spec is None or spec.loader is None:
    raise SystemExit("Unable to load Sprint 8C final closure runner")
base = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = base
spec.loader.exec_module(base)


class FinalClosureV2(base.Closure):
    """Treat only the deliberately generated RBAC 403 browser console events as expected."""

    def check(self, category: str, name: str, condition: bool, detail="") -> None:
        if category == "Browser evidence" and name == "no console errors":
            recorded = list(self.report["browser"].get("console_errors", []))
            expected = [
                item
                for item in recorded
                if item.get("label") in {"manager-denial", "analyst-denial"}
                and "status of 403" in str(item.get("text", ""))
            ]
            unexpected = [item for item in recorded if item not in expected]
            self.report["browser"]["expected_rbac_console_denials"] = len(expected)
            self.report["browser"]["console_errors"] = unexpected
            condition = not unexpected
            detail = unexpected[:3]
        return super().check(category, name, condition, detail)


if __name__ == "__main__":
    base.OUT.mkdir(parents=True, exist_ok=True)
    exit_code = FinalClosureV2().run()
    report = json.loads(base.REPORT_PATH.read_text(encoding="utf-8"))
    print(json.dumps({"decision": report["decision"], "report": str(base.REPORT_PATH)}, ensure_ascii=False))
    raise SystemExit(exit_code)
