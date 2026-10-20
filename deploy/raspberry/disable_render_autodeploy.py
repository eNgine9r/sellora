"""Bounded Render retirement; preserves the service, environment and database."""
import json
import os
import time
from urllib.request import Request, urlopen

SERVICE_ID = "srv-d8g092m7r5hc73aitgng"
SERVICE_NAME = "sellora-api-staging"
URL = "https://api.render.com/v1/services/" + SERVICE_ID
HEALTH_URL = "https://btc-radar.tail7f9b04.ts.net/sellora-health"
EXPECTED_RUNTIME = "37a20fd3d848406d92a71505c26995fe0edd937d"


def main():
    key = os.environ["RENDER_API_KEY"]
    assert key, "Render API credential missing"
    retire = os.getenv("RENDER_RETIRE_SERVICE", "false") == "true"

    def request(method="GET", payload=None, suffix=""):
        assert suffix in {"", "/suspend"}, "Unexpected Render operation"
        data = None if payload is None else json.dumps(payload).encode()
        headers = {"Authorization": "Bearer " + key, "Accept": "application/json"}
        if data is not None:
            headers["Content-Type"] = "application/json"
        with urlopen(Request(URL + suffix, data=data, headers=headers, method=method), timeout=30) as response:
            raw = response.read()
            return response.status, json.loads(raw) if raw else {}

    def identify(service):
        assert service.get("id") == SERVICE_ID, "Unexpected service ID"
        assert service.get("name") == SERVICE_NAME, "Unexpected service name"
        assert service.get("type") == "web_service", "Unexpected service type"

    _, service = request()
    identify(service)
    if retire and service.get("suspended") != "suspended":
        with urlopen(HEALTH_URL, timeout=20) as response:
            health = json.load(response)
        assert health.get("status") == "ok", "Raspberry is not healthy"
        assert health.get("runtime_commit") == EXPECTED_RUNTIME, "Unexpected Raspberry release"
        assert health.get("meta_webhook_worker_enabled") is False, "Raspberry worker already enabled"
        assert health.get("meta_webhook_worker_running") is False, "Raspberry worker already running"
    if service.get("autoDeployTrigger") != "off":
        request("PATCH", {"autoDeployTrigger": "off"})
    _, updated = request()
    identify(updated)
    assert updated.get("autoDeployTrigger") == "off", "Render native autodeploy remains active"
    if retire and updated.get("suspended") != "suspended":
        code, _ = request("POST", suffix="/suspend")
        assert code == 202, "Render did not accept service suspension"
        for _ in range(15):
            _, updated = request()
            identify(updated)
            if updated.get("suspended") == "suspended":
                break
            time.sleep(2)
        else:
            raise AssertionError("Render suspension was not confirmed")
    print(json.dumps({
        "service_id": SERVICE_ID, "auto_deploy": "off",
        "suspension": updated.get("suspended", "unknown"),
        "deleted_resources": 0,
    }))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        # Never emit provider exceptions containing credential or request details.
        raise SystemExit("Render retirement step failed: " + type(error).__name__ + (
            ": " + str(error) if isinstance(error, AssertionError) else ""
        ))
