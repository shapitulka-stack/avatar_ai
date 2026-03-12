from __future__ import annotations

import mimetypes
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from app.config import Settings


@dataclass
class DownloadedObject:
    content: bytes
    content_type: str | None = None


class StorageError(RuntimeError):
    pass


def normalize_storage_key(key: str) -> str:
    candidate = str(PurePosixPath(key)).lstrip("/")
    if not candidate or candidate == "." or candidate.startswith("..") or "/../" in candidate:
        raise StorageError("Invalid storage key.")
    return candidate.replace("\\", "/")


class LocalStorage:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def save_bytes(self, key: str, content: bytes, content_type: str | None = None) -> str:
        normalized = normalize_storage_key(key)
        path = self.root / normalized
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return normalized

    def download(self, key: str) -> DownloadedObject:
        normalized = normalize_storage_key(key)
        path = self.root / normalized
        if not path.exists():
            raise StorageError(f"Storage key '{normalized}' was not found.")
        content_type = mimetypes.guess_type(path.name)[0]
        return DownloadedObject(content=path.read_bytes(), content_type=content_type)


class S3Storage:
    def __init__(self, settings: Settings) -> None:
        if not settings.s3_bucket_name:
            raise StorageError("S3_BUCKET_NAME is required when STORAGE_BACKEND=s3.")

        try:
            import boto3
            from botocore.exceptions import BotoCoreError, ClientError
        except ImportError as exc:
            raise StorageError("Install boto3 to use STORAGE_BACKEND=s3.") from exc

        self.bucket = settings.s3_bucket_name
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            region_name=settings.s3_region_name,
            aws_access_key_id=settings.s3_access_key_id,
            aws_secret_access_key=settings.s3_secret_access_key,
        )
        self._errors: tuple[type[BaseException], ...] = (BotoCoreError, ClientError)

    def save_bytes(self, key: str, content: bytes, content_type: str | None = None) -> str:
        normalized = normalize_storage_key(key)
        try:
            self.client.put_object(
                Bucket=self.bucket,
                Key=normalized,
                Body=content,
                ContentType=content_type or "application/octet-stream",
            )
        except self._errors as exc:
            raise StorageError(f"Could not store '{normalized}' in S3.") from exc
        return normalized

    def download(self, key: str) -> DownloadedObject:
        normalized = normalize_storage_key(key)
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=normalized)
        except self._errors as exc:
            raise StorageError(f"Could not read '{normalized}' from S3.") from exc
        return DownloadedObject(
            content=response["Body"].read(),
            content_type=response.get("ContentType"),
        )


def get_storage(settings: Settings) -> LocalStorage | S3Storage:
    if settings.storage_backend.lower() == "s3":
        return S3Storage(settings)
    return LocalStorage(settings.storage_root)
