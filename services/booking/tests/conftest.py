import os
import sys
from datetime import datetime, timedelta, timezone

import boto3
import jwt
import pytest
from moto import mock_aws

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
SECRET = "test-secret-key-that-is-at-least-32-bytes"
os.environ.update(AWS_ACCESS_KEY_ID="test", AWS_SECRET_ACCESS_KEY="test",
                  AWS_REGION="us-east-1", TABLE_PREFIX="test-", JWT_SECRET=SECRET)
os.environ.pop("DYNAMODB_ENDPOINT", None)

ROOMS = {"per-1": {"roomId": "per-1", "locationId": "perth", "name": "Kinnoull",
                   "capacity": 15, "basePrice": 140}}
FORECAST_TEMP = 26  # |26 - 20| = 6 -> 20% surcharge


def token_for(email="alice@example.com", name="Alice"):
    exp = datetime.now(timezone.utc) + timedelta(hours=1)
    return jwt.encode({"sub": email, "name": name, "exp": exp}, SECRET, algorithm="HS256")


@pytest.fixture
def auth():
    return {"Authorization": f"Bearer {token_for()}"}


@pytest.fixture
def client(monkeypatch):
    with mock_aws():
        boto3.client("dynamodb", region_name="us-east-1").create_table(
            TableName="test-Bookings",
            KeySchema=[{"AttributeName": "roomId", "KeyType": "HASH"},
                       {"AttributeName": "date", "KeyType": "RANGE"}],
            AttributeDefinitions=[{"AttributeName": "roomId", "AttributeType": "S"},
                                  {"AttributeName": "date", "AttributeType": "S"},
                                  {"AttributeName": "userEmail", "AttributeType": "S"}],
            GlobalSecondaryIndexes=[{"IndexName": "userEmail-index",
                                     "KeySchema": [{"AttributeName": "userEmail", "KeyType": "HASH"}],
                                     "Projection": {"ProjectionType": "ALL"}}],
            BillingMode="PAY_PER_REQUEST",
        )
        import app as booking_app

        def fake_room(room_id):
            if room_id not in ROOMS:
                raise booking_app.UpstreamError("Room not found", 404)
            return ROOMS[room_id]

        def fake_forecast(location_id, day):
            return {"location": "Perth", "locationId": location_id, "date": day,
                    "temperature": FORECAST_TEMP}

        monkeypatch.setattr(booking_app, "get_room", fake_room)
        monkeypatch.setattr(booking_app, "get_forecast", fake_forecast)
        yield booking_app.create_app().test_client()
