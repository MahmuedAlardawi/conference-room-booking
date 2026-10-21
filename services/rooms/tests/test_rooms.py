def test_health(client):
    assert client.get("/api/rooms/health").json["service"] == "rooms"


def test_list_locations_sorted(client):
    names = [loc["name"] for loc in client.get("/api/rooms/locations").json]
    assert names == ["Dundee", "Perth"]


def test_get_location_by_id_and_name(client):
    assert client.get("/api/rooms/locations/perth").json["name"] == "Perth"
    assert client.get("/api/rooms/locations/PERTH").json["locationId"] == "perth"
    assert client.get("/api/rooms/locations/Atlantis").status_code == 404


def test_rooms_for_location(client):
    rooms = client.get("/api/rooms/locations/dundee/rooms").json
    assert [r["roomId"] for r in rooms] == ["dun-1"]
    assert rooms[0]["basePrice"] == 150.5 and rooms[0]["capacity"] == 12
    assert client.get("/api/rooms/locations/nowhere/rooms").status_code == 404


def test_get_room(client):
    room = client.get("/api/rooms/per-1").json
    assert room["basePrice"] == 140 and isinstance(room["basePrice"], int)
    assert client.get("/api/rooms/missing").status_code == 404