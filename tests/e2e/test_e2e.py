"""End-to-end tests against the running stack (Docker Compose locally, or the ALB after deploy).

BASE_URL=http://localhost:8080 pytest tests/e2e
"""
import os
import uuid
from datetime import date, timedelta

import requests

BASE = os.getenv("BASE_URL", "http://localhost:8080").rstrip("/")
# Random future date so repeated runs against a live system don't collide.
DAY = (date.today() + timedelta(days=200 + uuid.uuid4().int % 300)).isoformat()


def new_user():
    email = f"e2e-{uuid.uuid4().hex[:8]}@example.com"
    resp = requests.post(f"{BASE}/api/auth/register",
                         json={"email": email, "name": "E2E Tester", "password": "password123"})
    assert resp.status_code == 201, resp.text
    return {"Authorization": f"Bearer {resp.json()['token']}"}


def test_all_services_healthy():
    for svc in ("auth", "rooms", "weather", "bookings"):
        assert requests.get(f"{BASE}/api/{svc}/health").status_code == 200, svc
    assert requests.get(f"{BASE}/").status_code == 200


def test_weather_is_stable_and_validated():
    first = requests.get(f"{BASE}/api/weather", params={"location": "Perth", "date": DAY}).json()
    again = requests.get(f"{BASE}/api/weather", params={"location": "perth", "date": DAY}).json()
    assert first["temperature"] == again["temperature"]
    assert again["source"] == "stored"
    past = requests.get(f"{BASE}/api/weather", params={"location": "Perth", "date": "2020-01-01"})
    assert past.status_code == 400
    assert requests.get(f"{BASE}/api/weather",
                        params={"location": "Atlantis", "date": DAY}).status_code == 404


def test_booking_flow():
    headers = new_user()
    room = requests.get(f"{BASE}/api/rooms/locations/dundee/rooms").json()[0]

    assert requests.post(f"{BASE}/api/bookings",
                         json={"roomId": room["roomId"], "date": DAY, "guests": 2}).status_code == 401

    quote = requests.get(f"{BASE}/api/bookings/quote",
                         params={"roomId": room["roomId"], "date": DAY}, headers=headers).json()
    weather = requests.get(f"{BASE}/api/weather", params={"location": "dundee", "date": DAY}).json()
    assert quote["temperature"] == weather["temperature"]

    resp = requests.post(f"{BASE}/api/bookings", headers=headers,
                         json={"roomId": room["roomId"], "date": DAY, "guests": 2})
    assert resp.status_code == 201, resp.text
    assert resp.json()["finalPrice"] == quote["finalPrice"]

    again = requests.post(f"{BASE}/api/bookings", headers=new_user(),
                          json={"roomId": room["roomId"], "date": DAY, "guests": 2})
    assert again.status_code == 409

    mine = requests.get(f"{BASE}/api/bookings/me", headers=headers).json()
    assert [b["date"] for b in mine] == [DAY]
