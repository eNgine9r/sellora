from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path, PurePosixPath
from tempfile import NamedTemporaryFile
from typing import Iterator, Protocol
from urllib.parse import quote, unquote, urlparse
from uuid import UUID

from app.core.config import Settings, get_settings


class ImportSourceStorageError(RuntimeError):
    """Safe storage error that never exposes credentials or provider payloads."""


class StorageBucket(Protocol):
    def upload(self, path: str, file, file_options: dict | None = None): ...
    def download(self, path: str) -> bytes: ...
    def remove(self, paths: list[str]): ...


class ImportSourceStorage:
    URI_SCHEME = "supabase"

    def __init__(self, settings: Settings | None = None, bucket: StorageBucket | None = None) -> None:
        self.settings = settings or get_settings()
        self.backend = self.settings.import_storage_backend.strip().lower()
        if self.backend not in {"local", "supabase"}:
            raise ImportSourceStorageError("Unsupported import storage backend")
        self._bucket = bucket

    def store(self, workspace_id: UUID, job_id: UUID, filename: str, content: bytes) -> str:
        safe_filename = self._safe_filename(filename)
        if self.backend == "local":
            directory = Path(self.settings.import_storage_path) / str(workspace_id) / str(job_id)
            directory.mkdir(parents=True, exist_ok=True)
            path = directory / safe_filename
            path.write_bytes(content)
            return str(path)

        object_key = self._object_key(workspace_id, job_id, safe_filename)
        try:
            self._storage_bucket().upload(
                object_key,
                content,
                file_options={
                    "content-type": self._content_type(safe_filename),
                    "cache-control": "no-store",
                    "upsert": "false",
                },
            )
        except Exception as exc:
            raise ImportSourceStorageError("Unable to persist import source file") from exc
        return self._uri(object_key)

    def read_bytes(self, location: str) -> bytes:
        if not self.is_remote(location):
            path = Path(location)
            if not path.is_file():
                raise ImportSourceStorageError("Import source file is unavailable")
            return path.read_bytes()

        bucket_name, object_key = self._parse_uri(location)
        if bucket_name != self.settings.import_storage_bucket:
            raise ImportSourceStorageError("Import source bucket is invalid")
        try:
            payload = self._storage_bucket().download(object_key)
        except Exception as exc:
            raise ImportSourceStorageError("Import source file is unavailable") from exc
        if not isinstance(payload, bytes):
            payload = bytes(payload)
        return payload

    @contextmanager
    def materialize(self, location: str) -> Iterator[str]:
        if not self.is_remote(location):
            path = Path(location)
            if not path.is_file():
                raise ImportSourceStorageError("Import source file is unavailable")
            yield str(path)
            return

        _bucket_name, object_key = self._parse_uri(location)
        suffix = Path(object_key).suffix.lower()
        payload = self.read_bytes(location)
        temporary = NamedTemporaryFile(prefix="sellora-import-", suffix=suffix, delete=False)
        temporary_path = Path(temporary.name)
        try:
            temporary.write(payload)
            temporary.flush()
            temporary.close()
            yield str(temporary_path)
        finally:
            try:
                temporary.close()
            except Exception:
                pass
            temporary_path.unlink(missing_ok=True)

    def delete(self, location: str) -> None:
        if not self.is_remote(location):
            path = Path(location)
            path.unlink(missing_ok=True)
            self._remove_empty_parents(path.parent)
            return

        bucket_name, object_key = self._parse_uri(location)
        if bucket_name != self.settings.import_storage_bucket:
            raise ImportSourceStorageError("Import source bucket is invalid")
        try:
            self._storage_bucket().remove([object_key])
        except Exception as exc:
            raise ImportSourceStorageError("Unable to remove import source file") from exc

    def is_remote(self, location: str) -> bool:
        return urlparse(location).scheme == self.URI_SCHEME

    def assert_workspace_job_location(self, location: str, workspace_id: UUID, job_id: UUID) -> None:
        if not self.is_remote(location):
            return
        _bucket_name, object_key = self._parse_uri(location)
        expected_prefix = f"{workspace_id}/{job_id}/"
        if not object_key.startswith(expected_prefix):
            raise ImportSourceStorageError("Import source location does not match the workspace and job")

    def _storage_bucket(self) -> StorageBucket:
        if self._bucket is not None:
            return self._bucket
        url = (self.settings.supabase_url or "").strip().rstrip("/")
        secret_key = (self.settings.supabase_secret_key or "").strip()
        bucket_name = self.settings.import_storage_bucket.strip()
        if not url or not secret_key or not bucket_name:
            raise ImportSourceStorageError("Supabase import storage is not configured")
        try:
            from supabase import create_client

            self._bucket = create_client(url, secret_key).storage.from_(bucket_name)
        except Exception as exc:
            raise ImportSourceStorageError("Supabase import storage is not configured") from exc
        return self._bucket

    def _object_key(self, workspace_id: UUID, job_id: UUID, filename: str) -> str:
        return str(PurePosixPath(str(workspace_id), str(job_id), filename))

    def _uri(self, object_key: str) -> str:
        encoded_key = quote(object_key, safe="/")
        return f"{self.URI_SCHEME}://{self.settings.import_storage_bucket}/{encoded_key}"

    def _parse_uri(self, location: str) -> tuple[str, str]:
        parsed = urlparse(location)
        if parsed.scheme != self.URI_SCHEME or not parsed.netloc:
            raise ImportSourceStorageError("Import source location is invalid")
        object_key = unquote(parsed.path.lstrip("/"))
        path = PurePosixPath(object_key)
        if not object_key or path.is_absolute() or ".." in path.parts:
            raise ImportSourceStorageError("Import source location is invalid")
        return parsed.netloc, str(path)

    def _safe_filename(self, filename: str) -> str:
        value = Path(filename).name.replace("/", "_").replace("\\", "_").strip()
        if not value or value in {".", ".."}:
            raise ImportSourceStorageError("Import source filename is invalid")
        return value

    def _content_type(self, filename: str) -> str:
        if filename.lower().endswith(".csv"):
            return "text/csv; charset=utf-8"
        return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    def _remove_empty_parents(self, directory: Path) -> None:
        root = Path(self.settings.import_storage_path).resolve()
        current = directory
        while True:
            try:
                resolved = current.resolve()
                if resolved == root or root not in resolved.parents:
                    return
                current.rmdir()
            except OSError:
                return
            current = current.parent
