import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("api_watchdog", Path("../deploy/raspberry/api_watchdog.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_recovery_needs_three_failed_probes_and_never_changes_image():
    state = {"expected_image": "release-a"}
    for number in range(2):
        decision, state = module.decide(state, "release-a", False, 2000)
        assert decision == "ALERT_HTTP_UNRESPONSIVE"
    decision, state = module.decide(state, "release-a", False, 2000)
    assert decision == "RESTART_SAME_IMAGE"
    assert state["last_restart"] == 2000
    for _ in range(4):
        decision, state = module.decide(state, "release-a", False, 2100)
        assert decision != "RESTART_SAME_IMAGE"
    decision, state = module.decide(state, "new-release-b", False, 5000)
    assert decision == "BLOCKED_IMAGE_CHANGED"


def test_healthy_probe_resets_failure_streak():
    state = {"expected_image": "release-a", "failures": 2}
    decision, state = module.decide(state, "release-a", True, 2000)
    assert decision == "HEALTHY" and state["failures"] == 0
