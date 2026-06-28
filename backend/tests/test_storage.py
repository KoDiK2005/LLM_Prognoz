import uuid

import boto3
import pytest
from moto import mock_aws

from app.core.config import settings
from app.services.storage import STORAGE_ROOT, LocalStorage, S3Storage
from tests.conftest import register

VALID_CSV = b"date,value\n" + b"\n".join(
    f"2024-01-{day:02d},{100 + day}".encode() for day in range(1, 15)
)


@pytest.fixture
def s3_bucket(monkeypatch):
    monkeypatch.setattr(settings, "s3_bucket", "test-bucket")
    monkeypatch.setattr(settings, "s3_region", "us-east-1")
    monkeypatch.setattr(settings, "s3_endpoint_url", None)
    with mock_aws():
        boto3.client("s3", region_name="us-east-1").create_bucket(Bucket="test-bucket")
        yield


def test_s3_storage_round_trip(s3_bucket):
    backend = S3Storage()
    key = backend.save(uuid.uuid4(), "data.csv", b"date,value\n2024-01-01,1\n")
    assert backend.read(key) == b"date,value\n2024-01-01,1\n"


def test_s3_storage_keys_are_namespaced_by_org(s3_bucket):
    backend = S3Storage()
    org_id = uuid.uuid4()
    key = backend.save(org_id, "data.csv", b"x")
    assert key.startswith(f"{org_id}/")


def test_local_storage_rejects_path_traversal_in_filename():
    """file.filename on a multipart upload is attacker-controlled. A name
    like "x/../../../etc/passwd" must not let the write escape STORAGE_ROOT.
    """
    backend = LocalStorage()
    org_id = uuid.uuid4()
    try:
        relative_path = backend.save(org_id, "x/../../../../etc/passwd", b"pwned")
        resolved = (STORAGE_ROOT / relative_path).resolve()
        assert STORAGE_ROOT.resolve() in resolved.parents
        assert resolved.name.endswith("_passwd")
    finally:
        backend.delete(relative_path)


async def test_upload_and_forecast_work_with_s3_backend(client, s3_bucket, monkeypatch):
    monkeypatch.setattr(settings, "storage_backend", "s3")

    headers = await register(client, email="s3user@example.com")
    upload = await client.post(
        "/datasets/upload",
        headers=headers,
        files={"file": ("data.csv", VALID_CSV, "text/csv")},
        data={"date_column": "date", "value_column": "value", "name": "s3-series"},
    )
    assert upload.status_code == 201
    dataset_id = upload.json()["id"]

    created = await client.post(
        "/forecasts", headers=headers, json={"dataset_id": dataset_id, "horizon": 5}
    )
    run_id = created.json()["id"]

    fetched = await client.get(f"/forecasts/{run_id}", headers=headers)
    assert fetched.json()["status"] == "completed"
