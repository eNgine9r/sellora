#!/usr/bin/env python3
"""Retry-hardened entrypoint for Sprint 8A.1 browser/mobile QA."""
from __future__ import annotations

import importlib.util
import socket
import sys
import time
import urllib.error
from pathlib import Path

MODULE_PATH = Path(__file__).with_name("staging_browser_mobile_qa_v2.py")
spec = importlib.util.spec_from_file_location("sellora_browser_qa_v2", MODULE_PATH)
if spec is None or spec.loader is None:
    raise SystemExit("Unable to load browser QA v2 module")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

original_api_json = module.api_json


def retry_api_json(method, url, payload=None, headers=None):
    last_error = None
    last_result = None
    for attempt in range(1, 7):
        try:
            status, result = original_api_json(method, url, payload, headers)
            last_result = (status, result)
            if status < 500:
                return status, result
            last_error = RuntimeError(f"HTTP {status}")
        except (TimeoutError, socket.timeout, urllib.error.URLError, OSError) as exc:
            last_error = exc
        if attempt < 6:
            time.sleep(min(5 * attempt, 20))
    if last_result is not None:
        return last_result
    raise RuntimeError(f"staging API unavailable after retries: {type(last_error).__name__}")


module.api_json = retry_api_json

if __name__ == "__main__":
    required = [
        "STAGING_FRONTEND_URL",
        "STAGING_API_URL",
        "STAGING_OWNER_EMAIL",
        "STAGING_OWNER_PASSWORD",
        "STAGING_TEST_WORKSPACE_ID",
        "STAGING_SECOND_WORKSPACE_ID",
    ]
    missing = [name for name in required if not module.env(name)]
    if missing:
        print("Missing required browser QA inputs", file=sys.stderr)
        raise SystemExit(2)
    result = module.BrowserQa().run()
    print(f"Browser/mobile QA decision: {result}")
    raise SystemExit(0 if result == "PASS" else 1)
