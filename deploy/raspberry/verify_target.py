"""Read-only business canary using existing staging test credentials in Actions."""
import json
import os
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from uuid import uuid4

def main():
    base = os.environ["TARGET_API_URL"].rstrip("/")
    url = urlsplit(base)
    assert url.scheme == "https" and url.hostname == os.environ["TARGET_EXPECTED_HOST"]
    assert url.path == "/api/v1" and not url.query and not url.fragment
    def request(path, *, body=None, token=None, workspace=None):
        headers = {"Accept": "application/json"}
        if token:
            headers["Authorization"] = "Bearer " + token
        if workspace:
            headers["X-Workspace-ID"] = workspace
        payload = None
        if body is not None:
            payload = json.dumps(body).encode()
            headers["Content-Type"] = "application/json"
        try:
            with urlopen(Request(base + path, data=payload, headers=headers), timeout=45) as response:
                return response.status, json.load(response)
        except HTTPError as error:
            return error.code, {}
    code, _ = request("/auth/me")
    assert code == 401, "Anonymous route protection"
    code, pair = request("/auth/login", body={
        "email": os.environ["STAGING_OWNER_EMAIL"],
        "password": os.environ["STAGING_OWNER_PASSWORD"],
    })
    assert code == 200 and pair.get("access_token"), "Staging canary login"
    code, renewed = request("/auth/refresh", body={"refresh_token": pair["refresh_token"]})
    assert code == 200 and renewed.get("access_token"), "Canary token refresh"
    token = renewed["access_token"]
    code, user = request("/auth/me", token=token)
    assert code == 200 and user.get("is_active"), "Canary current user"
    memberships = user.get("memberships", [])
    assert memberships, "Existing canary memberships"
    evidence = {
        "target_api": base, "anonymous_protection": True,
        "login": True, "refresh": True, "membership_count": len(memberships),
        "workspaces_checked": 0, "conversation_count": 0, "sample_message_count": 0,
    }
    for membership in memberships:
        workspace = str(membership["workspace_id"])
        code, status = request("/onboarding/status", token=token, workspace=workspace)
        assert code == 200, "Existing workspace onboarding read"
        code, conversations = request("/direct/conversations", token=token, workspace=workspace)
        assert code == 200 and isinstance(conversations, list), "Existing Direct read"
        evidence["workspaces_checked"] += 1
        evidence["conversation_count"] += len(conversations)
        if conversations:
            code, messages = request("/direct/conversations/" + conversations[0]["id"] + "/messages",
                                     token=token, workspace=workspace)
            assert code == 200 and isinstance(messages, list), "Existing message history read"
            evidence["sample_message_count"] += len(messages)
    code, _ = request("/direct/conversations", token=token, workspace=str(uuid4()))
    assert code == 403, "Unknown workspace must reject authenticated access"
    evidence["foreign_workspace_rejected"] = True
    print(json.dumps(evidence))

if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        raise SystemExit("Target canary failed: " + type(error).__name__ + (
            ": " + str(error) if isinstance(error, AssertionError) else ""))
