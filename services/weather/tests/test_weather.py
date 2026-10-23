from datetime import date, timedelta

TOMORROW = (date.today() + timedelta(days=1)).isoformat()


def get(client, location="perth", day=TOMORROW):
    return client.get("/api/weather", query_string={"location": location, "date": day})


def test_health(client):
    assert client.get("/api/weather/health").json["service"] == "weather"


def test_generates_integer_in_range(client):
    resp = get(client)
    assert resp.status_code == 200
    body = resp.json
    assert body["location"] == "Perth" and body["date"] == TOMORROW
    assert isinstance(body["temperature"], int) and -5 <= body["temperature"] <= 35
    assert body["source"] == "generated"


def test_repeat_call_returns_same_stored_temperature(client):
    first = get(client).json
    for _ in range(5):
        again = get(client).json
        assert again["temperature"] == first["temperature"]
        assert again["source"] == "stored"


def test_name_and_id_share_the_same_forecast(client):
    by_id = get(client, "perth").json["temperature"]
    assert get(client, "Perth").json["temperature"] == by_id


def test_today_is_allowed(client):
    assert get(client, day=date.today().isoformat()).status_code == 200


def test_past_date_rejected(client):
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    resp = get(client, day=yesterday)
    assert resp.status_code == 400 and "error" in resp.json


def test_bad_date_format_rejected(client):
    assert get(client, day="01-06-2027").status_code == 400
    assert get(client, day="").status_code == 400


def test_unknown_location(client):
    resp = get(client, location="Atlantis")
    assert resp.status_code == 404 and resp.json["error"] == "Unknown location"


def test_missing_location(client):
    assert client.get("/api/weather", query_string={"date": TOMORROW}).status_code == 400