"""One-time, bounded retirement step; never deploys or deletes the old service."""
import json
import os
from urllib.error import HTTPError
from urllib.request import Request, urlopen

SERVICE_ID = "srv-d8g092m7r5hc73aitgng"
SERVICE_NAME = "sellora-api-staging"
URL = "https://api.render.com/v1/services/" + SERVICE_ID


def main():
    key = os.environ["RENDER_API_KEY"]
    assert key, "Render API credential missing"

    def request(method="GET", payload=None):
        data = None if payload is None else json.dumps(payload).encode()
        headers = {"Authorization": "Bearer " + key, "Accept": "application/json"}
        if data is not None:
            headers["Content-Type"] = "application/json"
        with urlopen(Request(URL, data=data, headers=headers, method=method), timeout=30) as response:
            return json.load(response)

    service = request()
    assert service.get("id") == SERVICE_ID, "Unexpected service ID"
    assert service.get("name") == SERVICE_NAME, "Unexpected service name"
    assert service.get("type") == "web_service", "Unexpected service type"
    request("PATCH", {"autoDeployTrigger": "off"})
    updated = request()
    assert updated.get("autoDeployTrigger") == "off", "Render native autodeploy remains active"
    print(json.dumps({
        "service_id": SERVICE_ID, "auto_deploy": "off",
        "suspension": "PENDING_WEBHOOK_CUTOVER",
        "deleted_resources": 0,
    }))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        # Provider exceptions can contain request details; emit only safe diagnostics.
        raise SystemExit("Render retirement step failed: " + type(error).__name__ + (
            ": " + str(error) if isinstance(error, AssertionError) else ""
        ))
