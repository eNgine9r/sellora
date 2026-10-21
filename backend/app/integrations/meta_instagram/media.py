"""Private Instagram attachment handling.

Provider URLs are secrets: they stay in workspace-scoped JSONB and never enter
the Direct API payload. Media is fetched only from trusted Meta CDN hosts.
"""
from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlsplit
from uuid import UUID

import httpx

ALLOWED_CDN_HOSTS = ("lookaside.fbsbx.com", "fbcdn.net", "fbsbx.com", "cdninstagram.com")
MAX_BYTES = 12 * 1024 * 1024
ALLOWED_MIMES = {
    "image/jpeg", "image/png", "image/webp", "image/gif",
    "video/mp4", "video/webm", "audio/mpeg", "audio/mp4",
    "audio/ogg", "audio/webm", "application/pdf",
}
MEDIA_LABELS = {
    "image": "Фото", "ig_post": "Допис Instagram", "video": "Відео",
    "audio": "Аудіо", "sticker": "Наліпка", "share": "Поширення",
    "reel": "Reels", "template": "Вкладення", "file": "Файл",
}


def valid_source_url(url: str) -> bool:
    if not isinstance(url, str) or len(url) > 8192:
        return False
    try:
        parsed = urlsplit(url)
        host = (parsed.hostname or "").lower().rstrip(".")
        port = parsed.port
    except ValueError:
        return False
    return (
        parsed.scheme == "https"
        and bool(host)
        and parsed.username is None
        and parsed.password is None
        and port in (None, 443)
        and not parsed.fragment
        and any(host == allowed or host.endswith("." + allowed) for allowed in ALLOWED_CDN_HOSTS)
    )


def normalize_attachments(message: dict) -> list[dict[str, str]]:
    raw = message.get("attachments")
    if isinstance(raw, dict):
        raw = [raw]
    elif not isinstance(raw, list):
        raw = []
    if isinstance(message.get("attachment"), dict):
        raw = [*raw, message["attachment"]]
    result: list[dict[str, str]] = []
    for item in raw[:30]:
        if not isinstance(item, dict):
            continue
        kind = str(item.get("type") or "file").lower()[:32]
        payload = item.get("payload")
        payload = payload if isinstance(payload, dict) else {}
        url = payload.get("url") or payload.get("media_url")
        source_url = url if isinstance(url, str) and valid_source_url(url) else None
        record: dict[str, str] = {"type": kind}
        if source_url:
            record["source_url"] = source_url
        result.append(record)
    return result


def public_attachments(metadata: dict | None) -> list[dict]:
    if not isinstance(metadata, dict):
        return []
    items = metadata.get("attachments")
    if not isinstance(items, list):
        return []
    return [
        {
            "index": index,
            "type": str(item.get("type") or "file")[:32],
            "label": MEDIA_LABELS.get(str(item.get("type") or "").lower(), "Вкладення"),
            "available": bool(item.get("source_url") or item.get("cached")),
        }
        for index, item in enumerate(items)
        if isinstance(item, dict)
    ]


def private_media_path(workspace_id: UUID, message_id: UUID, index: int) -> Path:
    root = Path(os.getenv("DIRECT_MEDIA_STORAGE_PATH", "/app/storage/direct-media"))
    return root / str(workspace_id) / str(message_id) / f"{index}.bin"


def _safe_fetch(url: str) -> tuple[bytes, str]:
    if not valid_source_url(url):
        raise ValueError("MEDIA_SOURCE_NOT_ALLOWED")
    current = url
    # Redirects remain restricted to trusted provider CDN hosts.
    with httpx.Client(timeout=15, follow_redirects=False, trust_env=False) as client:
        for _ in range(4):
            with client.stream("GET", current, headers={"Accept": "image/*,video/*,audio/*,application/pdf"}) as response:
                if response.status_code in (301, 302, 303, 307, 308):
                    location = response.headers.get("Location", "")
                    from urllib.parse import urljoin
                    current = urljoin(current, location)
                    if not valid_source_url(current):
                        raise ValueError("MEDIA_REDIRECT_NOT_ALLOWED")
                    continue
                if response.status_code != 200:
                    raise ValueError("MEDIA_SOURCE_UNAVAILABLE")
                mime = response.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
                if mime not in ALLOWED_MIMES:
                    raise ValueError("MEDIA_TYPE_NOT_ALLOWED")
                try:
                    length = int(response.headers.get("Content-Length", "0"))
                except ValueError:
                    length = 0
                if length > MAX_BYTES:
                    raise ValueError("MEDIA_TOO_LARGE")
                output = bytearray()
                for chunk in response.iter_bytes(chunk_size=65536):
                    output.extend(chunk)
                    if len(output) > MAX_BYTES:
                        raise ValueError("MEDIA_TOO_LARGE")
                if not output:
                    raise ValueError("MEDIA_EMPTY")
                return bytes(output), mime
    raise ValueError("MEDIA_TOO_MANY_REDIRECTS")


def cache_media(workspace_id: UUID, message_id: UUID, index: int, source_url: str) -> str:
    """Cache privately with atomic replacement. Never use a public/static path."""
    path = private_media_path(workspace_id, message_id, index)
    if path.exists():
        return "cached"
    data, mime = _safe_fetch(source_url)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(path.parent, 0o700)
    temp = path.with_suffix(".tmp")
    fd = os.open(str(temp), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)
    return mime


def cached_mime(metadata: dict | None, index: int) -> str | None:
    items = (metadata or {}).get("attachments")
    if not isinstance(items, list) or index < 0 or index >= len(items):
        return None
    item = items[index]
    if not isinstance(item, dict):
        return None
    mime = item.get("mime_type")
    if isinstance(mime, str) and mime in ALLOWED_MIMES:
        return mime
    kind = item.get("type")
    return {"image": "image/jpeg", "ig_post": "image/jpeg", "video": "video/mp4", "reel": "video/mp4"}.get(kind)
