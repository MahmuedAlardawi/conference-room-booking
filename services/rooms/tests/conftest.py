import os
import sys
from decimal import Decimal

import boto3
import pytest
from moto import mock_aws

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ.update(AWS_ACCESS_KEY_ID="test", AWS_SECRET_ACCESS_KEY="test",
                  AWS_REGION="us-east-1", TABLE_PREFIX="test-")
os.environ.pop("DYNAMODB_ENDPOINT", None)


@pytest.fixture
def client():
    with mock_aws():
        ddb = boto3.resource("dynamodb", region_name="us-east-1")
        ddb.create_table(
            TableName="test-Locations",
            KeySchema=[{"AttributeName": "locationId", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "locationId", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        ddb.create_table(
            TableName="test-Rooms",
            KeySchema=[{"AttributeName": "roomId", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "roomId", "AttributeType": "S"},
                                  {"AttributeName": "locationId", "AttributeType": "S"}],
            GlobalSecondaryIndexes=[{"IndexName": "locationId-index",
                                     "KeySchema": [{"AttributeName": "locationId", "KeyType": "HASH"}],
                                     "Projection": {"ProjectionType": "ALL"}}],
            BillingMode="PAY_PER_REQUEST",
        )
        ddb.Table("test-Locations").put_item(Item={"locationId": "perth", "name": "Perth"})
        ddb.Table("test-Locations").put_item(Item={"locationId": "dundee", "name": "Dundee"})
        ddb.Table("test-Rooms").put_item(Item={"roomId": "per-1", "locationId": "perth", "name": "Kinnoull",
                                               "capacity": 15, "basePrice": Decimal("140")})
        ddb.Table("test-Rooms").put_item(Item={"roomId": "dun-1", "locationId": "dundee", "name": "Tay",
                                               "capacity": 12, "basePrice": Decimal("150.50")})
        from app import create_app
        yield create_app().test_client()