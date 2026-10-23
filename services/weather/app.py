"""Weather Forecast Service (stand-alone).

GET /api/weather?location=<id or name>&date=YYYY-MM-DD
Returns a stored forecast, or generates a random integer, stores it and returns it.
"""
import os
import random
from datetime import date, datetime

import requests
from botocore.exceptions import ClientError
from flask import Flask, jsonify, request

from db import table

PREFIX = "/api/weather"
MIN_TEMP, MAX_TEMP = -5, 35


def rooms_url():
    return os.getenv("ROOMS_URL", "http://rooms:5000")


def lookup_location(id_or_name):
    """Ask the Room Service whether the location exists. Returns dict or None."""
    resp = requests.get(f"{rooms_url()}/api/rooms/locations/{id_or_name}", timeout=3)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return resp.json()


def parse_date(text):
    try:
        return datetime.strptime(text or "", "%Y-%m-%d").date()
    except ValueError:
        return None


def error(message, status=400):
    return jsonify(error=message), status


def create_app():
    app = Flask(__name__)

    @app.get(f"{PREFIX}/health")
    def health():
        return jsonify(status="ok", service="weather")

    @app.get(PREFIX)
    def forecast():
        location_arg = (request.args.get("location") or "").strip()
        date_arg = request.args.get("date")
        if not location_arg:
            return error("location is required")

        day = parse_date(date_arg)
        if day is None:
            return error("date must be in YYYY-MM-DD format")
        if day < date.today():
            return error("date must be today or in the future")

        loc = lookup_location(location_arg)
        if loc is None:
            return error("Unknown location", 404)

        weather = table("Weather")
        key = {"locationId": loc["locationId"], "date": day.isoformat()}
        item = weather.get_item(Key=key).get("Item")
        source = "stored"
        if not item:
            item = {**key, "temperature": random.randint(MIN_TEMP, MAX_TEMP)}
            try:
                # Only the first writer wins, so the same date + location never changes.
                weather.put_item(Item=item,
                                 ConditionExpression="attribute_not_exists(locationId)")
                source = "generated"
            except ClientError as e:
                if e.response["Error"]["Code"] != "ConditionalCheckFailedException":
                    raise
                item = weather.get_item(Key=key)["Item"]

        return jsonify(
            location=loc["name"],
            locationId=loc["locationId"],
            date=day.isoformat(),
            temperature=int(item["temperature"]),
            unit="C",
            source=source,
        )

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)