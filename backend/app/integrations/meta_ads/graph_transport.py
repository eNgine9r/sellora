"""Bounded official-host transport. Credentials are never placed in request URLs."""
from __future__ import annotations

import httpx

from app.integrations.meta_ads.live_read_only_client import MetaReadOnlyClientError, MetaReadOnlyErrorCode

SUPPORTED_ADS_VERSIONS = {"v26.0"}


class MetaGraphTransport:
    def __init__(self, version: str, *, client: httpx.Client | None = None):
        if version not in SUPPORTED_ADS_VERSIONS:
            raise MetaReadOnlyClientError(MetaReadOnlyErrorCode.CONFIG_MISSING)
        self.version = version
        self.client = client

    def request(self, path: str, *, token: str | None = None, form: dict | None = None, params: dict | None = None):
        # Paths are internal constants or validated numeric provider IDs.
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        try:
            with httpx.Client(timeout=10, follow_redirects=False) if self.client is None else _Borrow(self.client) as client:
                response = client.request("POST" if form is not None else "GET",
                    f"https://graph.facebook.com/{self.version}{path}", params=params,
                    data=form, headers=headers, timeout=10, follow_redirects=False)
                payload = response.json()
        except (httpx.RequestError, ValueError):
            raise MetaReadOnlyClientError(MetaReadOnlyErrorCode.NETWORK_ERROR) from None
        if not isinstance(payload, dict):
            raise MetaReadOnlyClientError(MetaReadOnlyErrorCode.MALFORMED_RESPONSE)
        error = payload.get("error")
        if response.status_code >= 300 or error:
            code = error.get("code") if isinstance(error, dict) else None
            sub = error.get("error_subcode") if isinstance(error, dict) else None
            kind = MetaReadOnlyErrorCode.UNKNOWN_ERROR
            if response.status_code == 429 or code in {4, 17, 32, 613, 80004}:
                kind = MetaReadOnlyErrorCode.RATE_LIMITED
            elif code == 190:
                kind = MetaReadOnlyErrorCode.TOKEN_EXPIRED if sub in {463, 467} else MetaReadOnlyErrorCode.TOKEN_INVALID
            elif code in {10, 200, 2500} or response.status_code == 403:
                kind = MetaReadOnlyErrorCode.PERMISSION_MISSING
            elif response.status_code >= 500:
                kind = MetaReadOnlyErrorCode.NETWORK_ERROR
            raise MetaReadOnlyClientError(kind)
        return payload


class _Borrow:
    def __init__(self, client):
        self.client = client

    def __enter__(self):
        return self.client

    def __exit__(self, *_):
        return False
