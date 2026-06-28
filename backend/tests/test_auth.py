from tests.conftest import register


async def test_register_creates_org_and_returns_token(client):
    resp = await client.post(
        "/auth/register",
        json={"org_name": "Acme", "email": "owner@example.com", "password": "testpass123"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


async def test_register_duplicate_email_conflicts(client):
    payload = {"org_name": "Acme", "email": "dup@example.com", "password": "testpass123"}
    first = await client.post("/auth/register", json=payload)
    assert first.status_code == 201

    second = await client.post("/auth/register", json={**payload, "org_name": "Other Org"})
    assert second.status_code == 409


async def test_login_success(client):
    await client.post(
        "/auth/register",
        json={"org_name": "Acme", "email": "login@example.com", "password": "testpass123"},
    )
    resp = await client.post(
        "/auth/login", json={"email": "login@example.com", "password": "testpass123"}
    )
    assert resp.status_code == 200
    assert resp.json()["access_token"]


async def test_login_wrong_password(client):
    await client.post(
        "/auth/register",
        json={"org_name": "Acme", "email": "wrongpw@example.com", "password": "testpass123"},
    )
    resp = await client.post(
        "/auth/login", json={"email": "wrongpw@example.com", "password": "nope"}
    )
    assert resp.status_code == 401


async def test_me_requires_valid_token(client):
    anon = await client.get("/auth/me")
    assert anon.status_code in (401, 403)

    headers = await register(client, email="me@example.com")
    resp = await client.get("/auth/me", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["email"] == "me@example.com"


async def test_login_rate_limited_after_repeated_attempts(client):
    await client.post(
        "/auth/register",
        json={"org_name": "Acme", "email": "bruteforce@example.com", "password": "testpass123"},
    )

    payload = {"email": "bruteforce@example.com", "password": "wrong"}
    statuses = [
        (await client.post("/auth/login", json=payload)).status_code for _ in range(11)
    ]

    assert statuses.count(429) >= 1
    assert statuses[:10] == [401] * 10
