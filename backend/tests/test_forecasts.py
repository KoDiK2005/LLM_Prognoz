import uuid

from app.models.dataset import Dataset
from app.models.forecast_run import ForecastRun, ForecastRunStatus
from tests.conftest import register

VALID_CSV = b"date,value\n" + b"\n".join(
    f"2024-01-{day:02d},{100 + day}".encode() for day in range(1, 15)
)


async def _upload_dataset(client, headers, name="series") -> str:
    resp = await client.post(
        "/datasets/upload",
        headers=headers,
        files={"file": ("data.csv", VALID_CSV, "text/csv")},
        data={"date_column": "date", "value_column": "value", "name": name},
    )
    return resp.json()["id"]


async def test_create_and_complete_forecast_run(client):
    headers = await register(client, email="forecast@example.com")
    dataset_id = await _upload_dataset(client, headers)

    created = await client.post(
        "/forecasts", headers=headers, json={"dataset_id": dataset_id, "horizon": 5}
    )
    assert created.status_code == 202
    assert created.json()["status"] == "pending"
    run_id = created.json()["id"]

    # The queue is stubbed to run the worker job inline (see conftest), so
    # by the time the POST above returns the job has already finished —
    # but the response was serialized before that, hence "pending" there.
    # A fresh GET (fresh DB session) sees the up-to-date row.
    fetched = await client.get(f"/forecasts/{run_id}", headers=headers)
    assert fetched.status_code == 200
    body = fetched.json()
    assert body["status"] == "completed"
    assert len(body["result"]["forecast"]) == 5


async def test_forecast_run_failure_is_recorded(client, db_session):
    headers = await register(client, email="failure@example.com")
    dataset_id = await _upload_dataset(client, headers)

    # Simulate the underlying file going missing between upload and run.
    dataset = await db_session.get(Dataset, uuid.UUID(dataset_id))
    dataset.storage_path = "does/not/exist.csv"
    await db_session.commit()

    created = await client.post(
        "/forecasts", headers=headers, json={"dataset_id": dataset_id, "horizon": 5}
    )
    run_id = created.json()["id"]

    fetched = await client.get(f"/forecasts/{run_id}", headers=headers)
    body = fetched.json()
    assert body["status"] == "failed"
    assert body["error_message"]


async def test_get_forecast_run_cross_org_404(client):
    headers_a = await register(client, email="cross-a@example.com", org_name="Org A")
    headers_b = await register(client, email="cross-b@example.com", org_name="Org B")
    dataset_id = await _upload_dataset(client, headers_a)

    created = await client.post(
        "/forecasts", headers=headers_a, json={"dataset_id": dataset_id, "horizon": 5}
    )
    run_id = created.json()["id"]

    resp = await client.get(f"/forecasts/{run_id}", headers=headers_b)
    assert resp.status_code == 404


async def test_delete_forecast_run_cascades_to_insights(client):
    headers = await register(client, email="delrun@example.com")
    dataset_id = await _upload_dataset(client, headers)

    created = await client.post(
        "/forecasts", headers=headers, json={"dataset_id": dataset_id, "horizon": 5}
    )
    run_id = created.json()["id"]
    await client.post(f"/forecasts/{run_id}/insights", headers=headers, json={"providers": ["openai"]})

    resp = await client.delete(f"/forecasts/{run_id}", headers=headers)
    assert resp.status_code == 204
    assert (await client.get(f"/forecasts/{run_id}", headers=headers)).status_code == 404


async def test_delete_forecast_run_cross_org_404(client):
    headers_a = await register(client, email="delrun-a@example.com", org_name="Org A")
    headers_b = await register(client, email="delrun-b@example.com", org_name="Org B")
    dataset_id = await _upload_dataset(client, headers_a)

    created = await client.post(
        "/forecasts", headers=headers_a, json={"dataset_id": dataset_id, "horizon": 5}
    )
    run_id = created.json()["id"]

    resp = await client.delete(f"/forecasts/{run_id}", headers=headers_b)
    assert resp.status_code == 404


async def test_list_forecast_runs_by_dataset(client):
    headers = await register(client, email="history@example.com")
    dataset_id = await _upload_dataset(client, headers)

    for horizon in (5, 10):
        await client.post(
            "/forecasts", headers=headers, json={"dataset_id": dataset_id, "horizon": horizon}
        )

    resp = await client.get(f"/forecasts?dataset_id={dataset_id}", headers=headers)
    assert resp.status_code == 200
    horizons = sorted(run["forecast_params"]["horizon"] for run in resp.json())
    assert horizons == [5, 10]


async def test_insights_require_completed_run(client, db_session):
    headers = await register(client, email="pending-insights@example.com")
    dataset_id = await _upload_dataset(client, headers)
    me = (await client.get("/auth/me", headers=headers)).json()

    run = ForecastRun(
        org_id=uuid.UUID(me["org_id"]),
        dataset_id=uuid.UUID(dataset_id),
        created_by=uuid.UUID(me["id"]),
        status=ForecastRunStatus.PENDING,
        forecast_params={"horizon": 5},
    )
    db_session.add(run)
    await db_session.commit()
    await db_session.refresh(run)

    resp = await client.post(
        f"/forecasts/{run.id}/insights", headers=headers, json={"providers": ["openai"]}
    )
    assert resp.status_code == 400


async def test_insights_generate_mock_and_list(client):
    headers = await register(client, email="insights@example.com")
    dataset_id = await _upload_dataset(client, headers)

    created = await client.post(
        "/forecasts", headers=headers, json={"dataset_id": dataset_id, "horizon": 5}
    )
    run_id = created.json()["id"]

    generated = await client.post(
        f"/forecasts/{run_id}/insights", headers=headers, json={"providers": ["openai"]}
    )
    assert generated.status_code == 202

    listed = await client.get(f"/forecasts/{run_id}/insights", headers=headers)
    assert listed.status_code == 200
    insights = listed.json()
    assert len(insights) == 1
    assert insights[0]["status"] == "completed"
    assert "mock response" in insights[0]["response_text"]


async def test_ask_question_returns_mock_answer(client):
    headers = await register(client, email="ask@example.com")
    dataset_id = await _upload_dataset(client, headers)

    created = await client.post(
        "/forecasts", headers=headers, json={"dataset_id": dataset_id, "horizon": 5}
    )
    run_id = created.json()["id"]

    resp = await client.post(
        f"/forecasts/{run_id}/ask",
        headers=headers,
        json={"question": "What's the overall trend?", "provider": "openai"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["question"] == "What's the overall trend?"
    assert "mock response" in body["answer"]
    assert body["provider"] == "openai"


async def test_ask_question_requires_completed_run(client, db_session):
    headers = await register(client, email="ask-pending@example.com")
    dataset_id = await _upload_dataset(client, headers)
    me = (await client.get("/auth/me", headers=headers)).json()

    run = ForecastRun(
        org_id=uuid.UUID(me["org_id"]),
        dataset_id=uuid.UUID(dataset_id),
        created_by=uuid.UUID(me["id"]),
        status=ForecastRunStatus.PENDING,
        forecast_params={"horizon": 5},
    )
    db_session.add(run)
    await db_session.commit()
    await db_session.refresh(run)

    resp = await client.post(
        f"/forecasts/{run.id}/ask", headers=headers, json={"question": "Why?", "provider": "openai"}
    )
    assert resp.status_code == 400


async def test_ask_question_unreachable_ollama_returns_error_text(client):
    headers = await register(client, email="ask-ollama@example.com")
    dataset_id = await _upload_dataset(client, headers)

    created = await client.post(
        "/forecasts", headers=headers, json={"dataset_id": dataset_id, "horizon": 5}
    )
    run_id = created.json()["id"]

    resp = await client.post(
        f"/forecasts/{run_id}/ask",
        headers=headers,
        json={"question": "Why?", "provider": "ollama"},
    )
    assert resp.status_code == 200
    assert "Error generating answer" in resp.json()["answer"]


async def test_queue_unavailable_returns_503_and_marks_run_failed(client, monkeypatch):
    import app.api.forecasts as forecasts_module
    from redis.exceptions import RedisError

    headers = await register(client, email="queuedown@example.com")
    dataset_id = await _upload_dataset(client, headers)

    async def broken_get_queue():
        raise RedisError("connection refused")

    monkeypatch.setattr(forecasts_module, "get_queue", broken_get_queue)

    resp = await client.post(
        "/forecasts", headers=headers, json={"dataset_id": dataset_id, "horizon": 5}
    )
    assert resp.status_code == 503
    listed = await client.get(f"/forecasts?dataset_id={dataset_id}", headers=headers)
    assert listed.json()[0]["status"] == "failed"


async def test_insights_unreachable_ollama_marked_failed(client):
    headers = await register(client, email="ollama-fail@example.com")
    dataset_id = await _upload_dataset(client, headers)

    created = await client.post(
        "/forecasts", headers=headers, json={"dataset_id": dataset_id, "horizon": 5}
    )
    run_id = created.json()["id"]

    await client.post(
        f"/forecasts/{run_id}/insights", headers=headers, json={"providers": ["ollama"]}
    )
    listed = await client.get(f"/forecasts/{run_id}/insights", headers=headers)
    insight = listed.json()[0]
    assert insight["status"] == "failed"
    assert "Error generating insight" in insight["response_text"]
