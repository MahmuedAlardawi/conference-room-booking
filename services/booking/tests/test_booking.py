from datetime import date, timedelta

from conftest import token_for

TOMORROW = (date.today() + timedelta(days=1)).isoformat()


def book(client, headers, **overrides):
    body = {"roomId": "per-1", "date": TOMORROW, "guests": 10, **overrides}
    return client.post("/api/bookings", json=body, headers=headers)


def test_health(client):
    assert client.get("/api/bookings/health").json["service"] == "booking"


def test_quote(client, auth):
    q = client.get("/api/bookings/quote", query_string={"roomId": "per-1", "date": TOMORROW},
                   headers=auth).json
    assert q["basePrice"] == 140 and q["temperature"] == 26
    assert q["surchargeRate"] == 0.2 and q["finalPrice"] == 168.0


def test_booking_requires_token(client):
    assert book(client, {}).status_code == 401
    assert book(client, {"Authorization": "Bearer nonsense"}).status_code == 401


def test_create_booking_stores_price(client, auth):
    resp = book(client, auth)
    assert resp.status_code == 201
    b = resp.json
    assert b["finalPrice"] == 168 and b["temperature"] == 26
    assert b["userEmail"] == "alice@example.com" and b["locationName"] == "Perth"


def test_double_booking_returns_409(client, auth):
    assert book(client, auth).status_code == 201
    other_user = {"Authorization": f"Bearer {token_for('bob@example.com', 'Bob')}"}
    resp = book(client, other_user)
    assert resp.status_code == 409 and "already booked" in resp.json["error"]


def test_capacity_and_guest_validation(client, auth):
    assert book(client, auth, guests=16).status_code == 400
    assert book(client, auth, guests=0).status_code == 400
    assert book(client, auth, guests="abc").status_code == 400


def test_date_validation(client, auth):
    past = (date.today() - timedelta(days=1)).isoformat()
    assert book(client, auth, date=past).status_code == 400
    assert book(client, auth, date="tomorrow").status_code == 400


def test_unknown_room(client, auth):
    assert book(client, auth, roomId="nope").status_code == 404


def test_my_bookings_only_shows_own(client, auth):
    day2 = (date.today() + timedelta(days=2)).isoformat()
    book(client, auth)
    book(client, auth, date=day2)
    bob = {"Authorization": f"Bearer {token_for('bob@example.com', 'Bob')}"}
    book(client, bob, date=(date.today() + timedelta(days=3)).isoformat())

    mine = client.get("/api/bookings/me", headers=auth).json
    assert [b["date"] for b in mine] == [TOMORROW, day2]
    assert len(client.get("/api/bookings/me", headers=bob).json) == 1