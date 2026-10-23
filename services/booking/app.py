"""Booking Service: quote a price, create a booking, list a user's bookings."""
import os
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from functools import wraps

import jwt
import requests
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError
from flask import Flask, g, jsonify, request

from db import table
from pricing import final_price, surcharge_rate

PREFIX = "/api/bookings"


def rooms_url():
    return os.getenv("ROOMS_URL", "http://rooms:5000")


def weather_url():
    return os.getenv("WEATHER_URL", "http://weather:5000")


class UpstreamError(Exception):
    def __init__(self, message, status):
        super().__init__(message)
        self.message, self.status = message, status


def get_room(room_id):
    resp = requests.get(f"{rooms_url()}/api/rooms/{room_id}", timeout=3)
    if resp.status_code == 404:
        raise UpstreamError("Room not found", 404)
    resp.raise_for_status()
    return resp.json()


def get_forecast(location_id, day):
    resp = requests.get(f"{weather_url()}/api/weather",
                        params={"location": location_id, "date": day}, timeout=3)
    if resp.status_code != 200:
        raise UpstreamError(resp.json().get("error", "Weather service error"),
                            resp.status_code)
    return resp.json()


def require_auth(view):
    """Verify the JWT locally with the shared signing key (no call to Auth)."""
    @wraps(view)
    def wrapper(*args, **kwargs):
        header = request.headers.get("Authorization", "")
        token = header[7:] if header.startswith("Bearer ") else ""
        try:
            claims = jwt.decode(token, os.getenv("JWT_SECRET", "dev-secret-change-me"),
                                algorithms=["HS256"])
        except jwt.PyJWTError:
            return jsonify(error="Authentication required"), 401
        g.email, g.name = claims["sub"], claims.get("name", "")
        return view(*args, **kwargs)
    return wrapper


def validate_day(text):
    try:
        day = datetime.strptime(text or "", "%Y-%m-%d").date()
    except ValueError:
        raise UpstreamError("date must be in YYYY-MM-DD format", 400)
    if day < date.today():
        raise UpstreamError("date must be today or in the future", 400)
    return day.isoformat()


def build_quote(room_id, day):
    room = get_room(room_id)
    forecast = get_forecast(room["locationId"], day)
    temp = forecast["temperature"]
    return {
        "roomId": room["roomId"],
        "roomName": room["name"],
        "locationId": room["locationId"],
        "locationName": forecast["location"],
        "capacity": room["capacity"],
        "date": day,
        "basePrice": float(room["basePrice"]),
        "temperature": temp,
        "surchargeRate": float(surcharge_rate(temp)),
        "finalPrice": float(final_price(room["basePrice"], temp)),
        "currency": "GBP",
    }


def to_json(item):
    """Convert DynamoDB Decimals to int/float for JSON."""
    def conv(v):
        if isinstance(v, Decimal):
            return int(v) if v == int(v) else float(v)
        return v
    return {k: conv(v) for k, v in item.items()}


def create_app():
    app = Flask(__name__)

    @app.errorhandler(UpstreamError)
    def upstream_error(e):
        return jsonify(error=e.message), e.status

    @app.get(f"{PREFIX}/health")
    def health():
        return jsonify(status="ok", service="booking")

    @app.get(f"{PREFIX}/quote")
    @require_auth
    def quote():
        room_id = request.args.get("roomId", "")
        day = validate_day(request.args.get("date"))
        return jsonify(build_quote(room_id, day))

    @app.post(PREFIX)
    @require_auth
    def create_booking():
        data = request.get_json(silent=True) or {}
        day = validate_day(data.get("date"))
        try:
            guests = int(data.get("guests", 0))
        except (TypeError, ValueError):
            guests = 0
        if guests < 1:
            return jsonify(error="guests must be at least 1"), 400

        q = build_quote(data.get("roomId", ""), day)
        if guests > q["capacity"]:
            return jsonify(error=f"Room capacity is {q['capacity']} guests"), 400

        booking = {
            "roomId": q["roomId"],
            "date": day,
            "bookingId": str(uuid.uuid4()),
            "userEmail": g.email,
            "userName": g.name,
            "roomName": q["roomName"],
            "locationId": q["locationId"],
            "locationName": q["locationName"],
            "guests": guests,
            "basePrice": Decimal(str(q["basePrice"])),
            "temperature": q["temperature"],
            "surchargeRate": Decimal(str(q["surchargeRate"])),
            "finalPrice": Decimal(str(q["finalPrice"])),
            "currency": "GBP",
            "createdAt": datetime.now(timezone.utc).isoformat(),
        }
        try:
            # Conditional write on (roomId, date) prevents double-booking without locks.
            table("Bookings").put_item(
                Item=booking,
                ConditionExpression="attribute_not_exists(roomId) AND attribute_not_exists(#d)",
                ExpressionAttributeNames={"#d": "date"},
            )
        except ClientError as e:
            if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
                return jsonify(error="Room already booked for this date"), 409
            raise
        return jsonify(to_json(booking)), 201

    @app.get(f"{PREFIX}/me")
    @require_auth
    def my_bookings():
        items = table("Bookings").query(
            IndexName="userEmail-index",
            KeyConditionExpression=Key("userEmail").eq(g.email),
        ).get("Items", [])
        return jsonify(sorted((to_json(i) for i in items), key=lambda b: b["date"]))

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)