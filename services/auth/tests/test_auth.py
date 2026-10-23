from datetime import datetime, timedelta, timezone

import jwt

USER = {"email": "Alice@Example.com", "name": "Alice", "password": "password123"}


def register(client, **overrides):
    return client.post("/api/auth/register", json={**USER, **overrides})


def test_health(client):
    assert client.get("/api/auth/health").json["status"] == "ok"


def test_register_returns_token(client):
    resp = register(client)
    assert resp.status_code == 201
    assert resp.json["email"] == "alice@example.com"  # normalised
    claims = jwt.decode(resp.json["token"], "test-secret-key-that-is-at-least-32-bytes", algorithms=["HS256"])
    assert claims["sub"] == "alice@example.com"


def test_password_is_hashed(client):
    register(client)
    from db import table
    item = table("Users").get_item(Key={"email": "alice@example.com"})["Item"]
    assert item["passwordHash"] != USER["password"]
    assert item["passwordHash"].startswith("$2")  # bcrypt


def test_duplicate_email_rejected(client):
    register(client)
    assert register(client).status_code == 409


def test_register_validation(client):
    assert register(client, email="not-an-email").status_code == 400
    assert register(client, name="").status_code == 400
    assert register(client, password="short").status_code == 400


def test_login_success_and_failure(client):
    register(client)
    ok = client.post("/api/auth/login", json={"email": "alice@example.com", "password": "password123"})
    assert ok.status_code == 200 and "token" in ok.json
    bad = client.post("/api/auth/login", json={"email": "alice@example.com", "password": "wrong"})
    assert bad.status_code == 401
    unknown = client.post("/api/auth/login", json={"email": "bob@example.com", "password": "x"})
    assert unknown.status_code == 401


def test_verify_token(client):
    token = register(client).json["token"]
    resp = client.get("/api/auth/verify", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200 and resp.json["email"] == "alice@example.com"


def test_verify_rejects_expired_and_missing_token(client):
    expired = jwt.encode({"sub": "a@b.com", "exp": datetime.now(timezone.utc) - timedelta(minutes=1)},
                         "test-secret-key-that-is-at-least-32-bytes", algorithm="HS256")
    assert client.get("/api/auth/verify", headers={"Authorization": f"Bearer {expired}"}).status_code == 401
    assert client.get("/api/auth/verify").status_code == 401
