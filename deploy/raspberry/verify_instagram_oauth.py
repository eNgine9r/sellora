"""Verify the public Instagram OAuth handoff without authorizing an account."""
from datetime import datetime, timezone
import json
import os
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

API = "https://sellora-web-staging.vercel.app/api/v1"
CALLBACK = "https://btc-radar.tail7f9b04.ts.net/api/v1/integrations/instagram/oauth/callback"
FRONTEND = "https://sellora-web-staging.vercel.app/settings/integrations/instagram/callback"
SCOPES = {"instagram_business_basic", "instagram_business_manage_messages"}


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def main():
    opener = build_opener(NoRedirect())

    def request(url, *, body=None, token=None, workspace=None):
        headers = {"Accept": "application/json"}
        if token:
            headers["Authorization"] = "Bearer " + token
        if workspace:
            headers["X-Workspace-ID"] = workspace
        data = None if body is None else json.dumps(body).encode()
        if data is not None:
            headers["Content-Type"] = "application/json"
        try:
            with opener.open(Request(url, data=data, headers=headers), timeout=30) as response:
                return response.status, json.load(response), response.headers
        except HTTPError as error:
            return error.code, {}, error.headers

    code, pair, _ = request(API + "/auth/login", body={
        "email": os.environ["STAGING_OWNER_EMAIL"],
        "password": os.environ["STAGING_OWNER_PASSWORD"],
    })
    assert code == 200 and pair.get("access_token"), "Owner login"
    token = pair["access_token"]
    code, user, _ = request(API + "/auth/me", token=token)
    assert code == 200, "Current user"
    owners = [m for m in user.get("memberships", []) if m.get("role") == "OWNER"]
    assert owners, "Existing owner membership"
    # This creates only a ten-minute OAuth state, never a connection or customer.
    code, handoff, _ = request(
        API + "/integrations/instagram/connect", body={},
        token=token, workspace=str(owners[0]["workspace_id"]),
    )
    assert code == 200, "Instagram connect"
    url = urlsplit(handoff["authorization_url"])
    query = parse_qs(url.query)
    assert url.scheme == "https" and url.hostname == "www.instagram.com", "Provider host"
    assert url.path == "/oauth/authorize" and not url.fragment, "Provider path"
    assert query.get("redirect_uri") == [CALLBACK], "Raspberry OAuth redirect"
    assert query.get("response_type") == ["code"], "OAuth response type"
    assert query.get("client_id") == ["1575856504325341"], "Existing Instagram app"
    assert len(query.get("state", [""])[0]) >= 32, "Opaque OAuth state"
    assert set(query.get("scope", [""])[0].split(",")) == SCOPES, "Minimal existing permissions"
    expiry = datetime.fromisoformat(handoff["expires_at"].replace("Z", "+00:00"))
    assert 0 < (expiry - datetime.now(timezone.utc)).total_seconds() <= 600, "State expiry"
    code, _, headers = request(CALLBACK + "?state=cutover-invalid-probe&code=invalid-probe")
    assert code == 303, "Public callback redirect"
    assert headers.get("Location") == FRONTEND + "?status=invalid_state", "Frontend return"
    print(json.dumps({
        "oauth_start": "PASS", "redirect_uri": CALLBACK,
        "public_callback": "PASS", "frontend_return": "PASS",
        "provider_account_authorization": "NOT_TESTED",
        "customer_mutations": 0, "outbound_messages": 0,
    }))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        # Never emit exception URLs, credentials, authorization URL or OAuth state.
        raise SystemExit("Instagram OAuth canary failed: " + type(error).__name__ + (
            ": " + str(error) if isinstance(error, AssertionError) else ""
        ))
