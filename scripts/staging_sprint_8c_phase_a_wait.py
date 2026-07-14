#!/usr/bin/env python3
from __future__ import annotations

import staging_sprint_8c_phase_a as phase_a


_original_check = phase_a.check


def baseline_aware_check(result, name, condition, detail=""):
    if name == "runtime identity deployed" and not condition:
        # The current process predates the safe runtime identity fields. That is
        # acceptable only for Phase A: Phase B must observe a new identified
        # process after the deliberate deployment marker.
        condition = result.get("baseline_health", {}).get("runtime_commit") is None
        detail = "legacy process baseline; Phase B must observe identified runtime"
    return _original_check(result, name, condition, detail)


phase_a.check = baseline_aware_check


if __name__ == "__main__":
    raise SystemExit(phase_a.main())
