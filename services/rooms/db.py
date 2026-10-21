"""DynamoDB helper. Uses DynamoDB Local when DYNAMODB_ENDPOINT is set."""
import os

import boto3


def table(name):
    resource = boto3.resource(
        "dynamodb",
        region_name=os.getenv("AWS_REGION", "us-east-1"),
        endpoint_url=os.getenv("DYNAMODB_ENDPOINT") or None,
    )
    return resource.Table(os.getenv("TABLE_PREFIX", "crb-") + name)