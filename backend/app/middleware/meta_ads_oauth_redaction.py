"""Remove Ads OAuth query credentials from the ASGI server's access-log scope."""


class MetaAdsOAuthQueryRedactionMiddleware:
    def __init__(self, app, *, callback_path="/api/v1/integrations/meta-ads/oauth/callback"):
        self.app = app
        self.callback_path = callback_path

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and scope.get("path", "").rstrip("/") == self.callback_path.rstrip("/"):
            # Uvicorn owns this outer scope and logs it when response headers start.
            # Preserve query parsing only in a private inner scope for FastAPI.
            inner = dict(scope)
            scope["query_string"] = b""
            async def protected_send(message):
                if message["type"] == "http.response.start":
                    message = dict(message)
                    headers = [(k, v) for k, v in message.get("headers", [])
                               if k.lower() not in {b"cache-control", b"referrer-policy"}]
                    message["headers"] = headers + [(b"cache-control", b"no-store"),
                                                    (b"referrer-policy", b"no-referrer")]
                await send(message)
            await self.app(inner, receive, protected_send)
        else:
            await self.app(scope, receive, send)
