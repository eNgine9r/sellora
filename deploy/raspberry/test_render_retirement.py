"""Offline checks for retirement guards; never uses provider credentials."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("retirement", Path(__file__).with_name("disable_render_autodeploy.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class Reply(io.BytesIO):
    def __init__(self, payload, status=200):
        super().__init__(json.dumps(payload).encode() if payload is not None else b"")
        self.status = status


class RetirementGuards(unittest.TestCase):
    def run_case(self, *, wrong_service=False, worker_running=False, already_suspended=False):
        calls = []
        suspended = already_suspended

        def fake_open(request, timeout):
            nonlocal suspended
            url = request if isinstance(request, str) else request.full_url
            method = "GET" if isinstance(request, str) else request.get_method()
            calls.append((method, url))
            if url == module.HEALTH_URL:
                return Reply({
                    "status": "ok", "runtime_commit": module.EXPECTED_RUNTIME,
                    "meta_webhook_worker_enabled": worker_running,
                    "meta_webhook_worker_running": worker_running,
                })
            if url == module.URL + "/suspend":
                self.assertEqual(method, "POST")
                suspended = True
                return Reply(None, 202)
            self.assertEqual(url, module.URL)
            return Reply({
                "id": "wrong-service" if wrong_service else module.SERVICE_ID,
                "name": module.SERVICE_NAME, "type": "web_service",
                "autoDeployTrigger": "off",
                "suspended": "suspended" if suspended else "not_suspended",
            })

        with patch.dict(os.environ, {"RENDER_API_KEY": "synthetic-test-key", "RENDER_RETIRE_SERVICE": "true"}):
            with patch.object(module, "urlopen", side_effect=fake_open):
                with contextlib.redirect_stdout(io.StringIO()) as output:
                    if wrong_service or (worker_running and not already_suspended):
                        with self.assertRaises(AssertionError):
                            module.main()
                    else:
                        module.main()
                        self.assertEqual(json.loads(output.getvalue())["suspension"], "suspended")
        return calls

    def test_wrong_service_never_mutated(self):
        calls = self.run_case(wrong_service=True)
        self.assertTrue(all(method == "GET" for method, _ in calls))

    def test_active_pi_worker_blocks_old_service_suspension(self):
        calls = self.run_case(worker_running=True)
        self.assertFalse(any(method == "POST" for method, _ in calls))

    def test_already_suspended_service_is_idempotent_with_active_pi_worker(self):
        calls = self.run_case(already_suspended=True, worker_running=True)
        self.assertTrue(all(method == "GET" for method, _ in calls))

    def test_pi_checked_before_verified_service_suspension(self):
        calls = self.run_case()
        health = calls.index(("GET", module.HEALTH_URL))
        suspend = calls.index(("POST", module.URL + "/suspend"))
        self.assertLess(health, suspend)
        self.assertEqual(sum(method == "POST" for method, _ in calls), 1)


if __name__ == "__main__":
    unittest.main()
