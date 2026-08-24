from __future__ import annotations

import hashlib
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .settings import InfrastructureSettings


@dataclass(frozen=True)
class StoredObject:
    key: str
    content_hash: str
    byte_size: int
    backend: str


class ContentStore(Protocol):
    def put(self, data: bytes, *, suffix: str = "") -> StoredObject: ...

    def get(self, key: str) -> bytes: ...

    def exists(self, key: str) -> bool: ...


def _normalized_suffix(suffix: str) -> str:
    if not suffix:
        return ""
    safe = "".join(ch for ch in suffix.lower() if ch.isalnum() or ch in {".", "-"})
    if safe and not safe.startswith("."):
        safe = "." + safe
    return safe[:16]


def object_key(data: bytes, suffix: str = "") -> tuple[str, str]:
    digest = hashlib.sha256(data).hexdigest()
    key = f"sha256/{digest[:2]}/{digest[2:4]}/{digest}{_normalized_suffix(suffix)}"
    return key, digest


class LocalContentStore:
    def __init__(self, root: str | Path):
        self.root = Path(root).expanduser().resolve()

    def _resolve(self, key: str) -> Path:
        candidate = (self.root / key).resolve()
        if self.root != candidate and self.root not in candidate.parents:
            raise ValueError("content key escapes storage root")
        return candidate

    def put(self, data: bytes, *, suffix: str = "") -> StoredObject:
        key, digest = object_key(data, suffix)
        destination = self._resolve(key)
        if not destination.exists():
            destination.parent.mkdir(parents=True, exist_ok=True)
            fd, temp_name = tempfile.mkstemp(prefix=".content-", dir=str(destination.parent))
            try:
                with os.fdopen(fd, "wb") as handle:
                    handle.write(data)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temp_name, destination)
            finally:
                if os.path.exists(temp_name):
                    os.unlink(temp_name)
        return StoredObject(key, digest, len(data), "local")

    def get(self, key: str) -> bytes:
        return self._resolve(key).read_bytes()

    def exists(self, key: str) -> bool:
        return self._resolve(key).is_file()


class S3ContentStore:
    def __init__(self, bucket: str, endpoint_url: str = ""):
        if not bucket:
            raise ValueError("S3 bucket is required")
        try:
            import boto3
        except ImportError as exc:
            raise RuntimeError("boto3 is required for the s3 content backend") from exc
        self.bucket = bucket
        self.client = boto3.client("s3", endpoint_url=endpoint_url or None)

    def put(self, data: bytes, *, suffix: str = "") -> StoredObject:
        key, digest = object_key(data, suffix)
        try:
            self.client.head_object(Bucket=self.bucket, Key=key)
        except Exception:
            self.client.put_object(Bucket=self.bucket, Key=key, Body=data)
        return StoredObject(key, digest, len(data), "s3")

    def get(self, key: str) -> bytes:
        return self.client.get_object(Bucket=self.bucket, Key=key)["Body"].read()

    def exists(self, key: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket, Key=key)
            return True
        except Exception:
            return False


def build_content_store(settings: InfrastructureSettings) -> ContentStore:
    if settings.content_backend == "s3":
        return S3ContentStore(settings.s3_bucket, settings.s3_endpoint_url)
    return LocalContentStore(settings.content_root)
