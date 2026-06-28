from app.core.config import settings
from tests.conftest import register

VALID_CSV = b"date,value\n" + b"\n".join(
    f"2024-01-{day:02d},{100 + day}".encode() for day in range(1, 15)
)


async def test_upload_valid_csv_creates_dataset(client):
    headers = await register(client, email="upload@example.com")
    resp = await client.post(
        "/datasets/upload",
        headers=headers,
        files={"file": ("data.csv", VALID_CSV, "text/csv")},
        data={"date_column": "date", "value_column": "value", "name": "my-series"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "my-series"
    assert body["column_mapping"] == {"date_column": "date", "value_column": "value"}


async def test_upload_missing_column_rejected(client):
    headers = await register(client, email="badcol@example.com")
    resp = await client.post(
        "/datasets/upload",
        headers=headers,
        files={"file": ("data.csv", VALID_CSV, "text/csv")},
        data={"date_column": "nope", "value_column": "value", "name": "x"},
    )
    assert resp.status_code == 400


async def test_upload_too_few_points_rejected(client):
    headers = await register(client, email="short@example.com")
    short_csv = b"date,value\n2024-01-01,1\n2024-01-02,2\n"
    resp = await client.post(
        "/datasets/upload",
        headers=headers,
        files={"file": ("data.csv", short_csv, "text/csv")},
        data={"date_column": "date", "value_column": "value", "name": "x"},
    )
    assert resp.status_code == 400


async def test_upload_over_size_limit_rejected(client, monkeypatch):
    monkeypatch.setattr(settings, "max_upload_size_mb", 0)
    headers = await register(client, email="toobig@example.com")
    resp = await client.post(
        "/datasets/upload",
        headers=headers,
        files={"file": ("data.csv", VALID_CSV, "text/csv")},
        data={"date_column": "date", "value_column": "value", "name": "x"},
    )
    assert resp.status_code == 413


async def test_list_datasets_scoped_to_org(client):
    headers_a = await register(client, email="orga@example.com", org_name="Org A")
    headers_b = await register(client, email="orgb@example.com", org_name="Org B")

    await client.post(
        "/datasets/upload",
        headers=headers_a,
        files={"file": ("data.csv", VALID_CSV, "text/csv")},
        data={"date_column": "date", "value_column": "value", "name": "org-a-dataset"},
    )

    resp_a = await client.get("/datasets", headers=headers_a)
    resp_b = await client.get("/datasets", headers=headers_b)

    assert [d["name"] for d in resp_a.json()] == ["org-a-dataset"]
    assert resp_b.json() == []


async def test_delete_dataset_cascades_to_runs_and_insights(client):
    headers = await register(client, email="deleteme@example.com")
    upload = await client.post(
        "/datasets/upload",
        headers=headers,
        files={"file": ("data.csv", VALID_CSV, "text/csv")},
        data={"date_column": "date", "value_column": "value", "name": "to-delete"},
    )
    dataset_id = upload.json()["id"]

    run = await client.post("/forecasts", headers=headers, json={"dataset_id": dataset_id, "horizon": 5})
    run_id = run.json()["id"]
    await client.post(f"/forecasts/{run_id}/insights", headers=headers, json={"providers": ["openai"]})

    resp = await client.delete(f"/datasets/{dataset_id}", headers=headers)
    assert resp.status_code == 204

    assert (await client.get(f"/forecasts/{run_id}", headers=headers)).status_code == 404
    assert (await client.get(f"/forecasts?dataset_id={dataset_id}", headers=headers)).status_code == 404


async def test_delete_dataset_cross_org_404(client):
    headers_a = await register(client, email="del-a@example.com", org_name="Org A")
    headers_b = await register(client, email="del-b@example.com", org_name="Org B")
    upload = await client.post(
        "/datasets/upload",
        headers=headers_a,
        files={"file": ("data.csv", VALID_CSV, "text/csv")},
        data={"date_column": "date", "value_column": "value", "name": "org-a-only"},
    )
    dataset_id = upload.json()["id"]

    resp = await client.delete(f"/datasets/{dataset_id}", headers=headers_b)
    assert resp.status_code == 404
