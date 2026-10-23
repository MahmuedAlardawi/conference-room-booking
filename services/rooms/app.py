"""Location & Room Service: lists locations and rooms (capacity, base price)."""
from decimal import Decimal

from boto3.dynamodb.conditions import Key
from flask import Flask, jsonify

from db import table

PREFIX = "/api/rooms"


def to_json(item):
    """Convert DynamoDB Decimals to int/float for JSON."""
    def conv(v):
        if isinstance(v, Decimal):
            return int(v) if v == int(v) else float(v)
        return v
    return {k: conv(v) for k, v in item.items()}


def find_location(id_or_name):
    """Look up a location by id, or by name (case-insensitive)."""
    locations = table("Locations")
    item = locations.get_item(Key={"locationId": id_or_name}).get("Item")
    if item:
        return item
    wanted = id_or_name.strip().lower()
    for loc in locations.scan().get("Items", []):  # small, seeded table
        if loc["name"].lower() == wanted:
            return loc
    return None


def create_app():
    app = Flask(__name__)

    @app.get(f"{PREFIX}/health")
    def health():
        return jsonify(status="ok", service="rooms")

    @app.get(f"{PREFIX}/locations")
    def list_locations():
        items = table("Locations").scan().get("Items", [])
        return jsonify(sorted((to_json(i) for i in items), key=lambda x: x["name"]))

    @app.get(f"{PREFIX}/locations/<id_or_name>")
    def get_location(id_or_name):
        loc = find_location(id_or_name)
        if not loc:
            return jsonify(error="Location not found"), 404
        return jsonify(to_json(loc))

    @app.get(f"{PREFIX}/locations/<id_or_name>/rooms")
    def list_rooms(id_or_name):
        loc = find_location(id_or_name)
        if not loc:
            return jsonify(error="Location not found"), 404
        items = table("Rooms").query(
            IndexName="locationId-index",
            KeyConditionExpression=Key("locationId").eq(loc["locationId"]),
        ).get("Items", [])
        return jsonify(sorted((to_json(i) for i in items), key=lambda x: x["name"]))

    @app.get(f"{PREFIX}/<room_id>")
    def get_room(room_id):
        room = table("Rooms").get_item(Key={"roomId": room_id}).get("Item")
        if not room:
            return jsonify(error="Room not found"), 404
        return jsonify(to_json(room))

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
