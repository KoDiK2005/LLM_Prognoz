import asyncio
import uuid
from pathlib import Path
from typing import Protocol

from app.core.config import settings

STORAGE_ROOT = Path(__file__).resolve().parent.parent.parent / "storage"


class StorageBackend(Protocol):
    def save(self, org_id: uuid.UUID, filename: str, content: bytes) -> str: ...
    def read(self, relative_path: str) -> bytes: ...


class LocalStorage:
    """Disk storage under ./storage — fine for a single-instance deploy,
    but the dataset CSV won't survive a redeploy that wipes the volume.
    """

    def save(self, org_id: uuid.UUID, filename: str, content: bytes) -> str:
        org_dir = STORAGE_ROOT / str(org_id)
        org_dir.mkdir(parents=True, exist_ok=True)

        path = org_dir / f"{uuid.uuid4()}_{filename}"
        path.write_bytes(content)
        return str(path.relative_to(STORAGE_ROOT))

    def read(self, relative_path: str) -> bytes:
        return (STORAGE_ROOT / relative_path).read_bytes()


class S3Storage:
    """Real S3, or any S3-compatible endpoint (MinIO, Cloudflare R2, ...)
    via `s3_endpoint_url`. The returned "path" is the object key.
    """

    def __init__(self) -> None:
        import boto3

        self._bucket = settings.s3_bucket
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url or None,
            region_name=settings.s3_region,
        )

    def save(self, org_id: uuid.UUID, filename: str, content: bytes) -> str:
        key = f"{org_id}/{uuid.uuid4()}_{filename}"
        self._client.put_object(Bucket=self._bucket, Key=key, Body=content)
        return key

    def read(self, relative_path: str) -> bytes:
        obj = self._client.get_object(Bucket=self._bucket, Key=relative_path)
        return obj["Body"].read()


def _get_backend() -> StorageBackend:
    if settings.storage_backend == "s3":
        return S3Storage()
    return LocalStorage()


async def save(org_id: uuid.UUID, filename: str, content: bytes) -> str:
    return await asyncio.to_thread(_get_backend().save, org_id, filename, content)


async def read(relative_path: str) -> bytes:
    return await asyncio.to_thread(_get_backend().read, relative_path)
