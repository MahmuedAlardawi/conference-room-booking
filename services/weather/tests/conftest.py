import os
import sys

import boto3
import pytest
from moto import mock_aws

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ.update(AWS_ACCESS_KEY_ID="test", AWS_SECRET_ACCESS_KEY="test",
                  AWS_REGION="us-east-1", TABLE_PREFIX="test-")
os.environ.pop("DYNAMODB_ENDPOINT", None)

KNOWN = {"perth": {"locationId": "perth", "name": "Perth"}}


def fake_lookup(id_or_name):
    """Stand-in for the Room Service call."""
    key = id_or_name.lower()
    return KNOWN.get(key) or next((v for v in KNOWN.values() if v["name"].lower() == key), None)


@pytest.fixture
def client(monkeypatch):
    with mock_aws():
        boto3.client("dynamodb", region_name="us-east-1").create_table(
            TableName="test-Weather",
            KeySchema=[{"AttributeName": "locationId", "KeyType": "HASH"},
                       {"AttributeName": "date", "KeyType": "RANGE"}],
            AttributeDefinitions=[{"AttributeName": "locationId", "AttributeType": "S"},
                                  {"AttributeName": "date", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        import app as weather_app
        monkeypatch.setattr(weather_app, "lookup_location", fake_lookup)
        yield weather_app.create_app().test_client()