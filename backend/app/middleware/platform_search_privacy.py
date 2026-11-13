"""Keep private platform inputs out of access logs and validation responses."""

from fastapi import Request
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


def is_platform_directory_path(path: str, directory_path: str) -> bool:
    return path.rstrip("/") in (directory_path, f"{directory_path}/search")


class PlatformSearchPrivacyMiddleware:
    def __init__(self, app, *, directory_path: str, user_search_path: str, mfa_path: str) -> None:
        self.app = app
        self.directory_path = directory_path
        self.mfa_path = mfa_path
        self.user_search_path = user_search_path

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] == "http" and (
            is_platform_directory_path(scope["path"], self.directory_path)
            or scope["path"].rstrip("/") in (self.mfa_path, self.user_search_path)
        ):
            # Uvicorn retains the outer scope to build its access-log message.
            inner = dict(scope)
            scope["query_string"] = b""
            # Resolve slash aliases here so FastAPI never reflects the query in Location.
            inner["path"] = inner["path"].rstrip("/")
            await self.app(inner, receive, send)
            return
        await self.app(scope, receive, send)


async def platform_validation_error(
    request: Request, exc: RequestValidationError, *, directory_path: str, user_search_path: str, mfa_path: str,
):
    if request.url.path.rstrip("/") == mfa_path:
        return JSONResponse(status_code=422, content={"detail": "Invalid MFA request"})
    if request.url.path.rstrip("/") == user_search_path:
        return JSONResponse(status_code=422, content={"detail": "Invalid user search filters"})
    if is_platform_directory_path(request.url.path, directory_path):
        return JSONResponse(status_code=422, content={"detail": "Invalid workspace list filters"})
    return await request_validation_exception_handler(request, exc)
