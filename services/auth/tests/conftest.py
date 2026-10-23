import os
import sys

import boto3
import pytest
from moto import mock_aws

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ.update(AWS_ACCESS_KEY_ID="test", AWS_SECRET_ACCESS_KEY="test",
                  AWS_REGION="us-east-1", TABLE_PREFIX="test-", JWT_SECRET="test-secret-key-that-is-at-least-32-bytes")
os.environ.pop("DYNAMODB_ENDPOINT", None)


@pytest.fixture
def client():
    with mock_aws():
        boto3.client("dynamodb", region_name="us-east-1").create_table(
            TableName="test-Users",
            KeySchema=[{"AttributeName": "email", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "email", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        from app import create_app
        yield create_app().test_client()
