"""Create the DynamoDB tables (if missing) and seed locations and rooms.

Local:  run by docker compose (DYNAMODB_ENDPOINT=http://dynamodb:8000)
AWS:    python scripts/setup_db.py   (uses your lab credentials)
"""
import os
import time
from decimal import Decimal

import boto3

PREFIX = os.getenv("TABLE_PREFIX", "crb-")

TABLES = {
    "Users": {"keys": [("email", "S", "HASH")]},
    "Locations": {"keys": [("locationId", "S", "HASH")]},
    "Rooms": {
        "keys": [("roomId", "S", "HASH")],
        "gsi": [("locationId-index", "locationId")],
    },
    "Weather": {"keys": [("locationId", "S", "HASH"), ("date", "S", "RANGE")]},
    "Bookings": {
        "keys": [("roomId", "S", "HASH"), ("date", "S", "RANGE")],
        "gsi": [("userEmail-index", "userEmail")],
    },
}

LOCATIONS = [
    ("dundee", "Dundee", "Waterfront Place, Dundee DD1 3BA"),
    ("edinburgh", "Edinburgh", "1 Princes Street, Edinburgh EH2 2EQ"),
    ("glasgow", "Glasgow", "100 Buchanan Street, Glasgow G1 2JA"),
    ("london", "London", "20 Canary Wharf, London E14 5AB"),
    ("manchester", "Manchester", "1 Spinningfields, Manchester M3 3AP"),
    ("perth", "Perth", "High Street, Perth PH1 5TH"),
]

# (roomId, locationId, name, capacity, basePrice in GBP)
ROOMS = [
    ("dun-tay", "dundee", "Tay Room", 12, 150),
    ("dun-discovery", "dundee", "Discovery Suite", 40, 400),
    ("edi-castle", "edinburgh", "Castle Room", 20, 250),
    ("edi-arthur", "edinburgh", "Arthur's Seat Hall", 80, 700),
    ("edi-forth", "edinburgh", "Forth Boardroom", 8, 120),
    ("gla-clyde", "glasgow", "Clyde Room", 25, 260),
    ("gla-merchant", "glasgow", "Merchant Hall", 60, 550),
    ("lon-thames", "london", "Thames Suite", 100, 1200),
    ("lon-docklands", "london", "Docklands Room", 30, 450),
    ("lon-canary", "london", "Canary Boardroom", 10, 300),
    ("man-irwell", "manchester", "Irwell Room", 16, 180),
    ("man-deansgate", "manchester", "Deansgate Hall", 50, 480),
    ("per-kinnoull", "perth", "Kinnoull Room", 15, 140),
]


def dynamodb():
    return boto3.resource(
        "dynamodb",
        region_name=os.getenv("AWS_REGION", "us-east-1"),
        endpoint_url=os.getenv("DYNAMODB_ENDPOINT") or None,
    )


def create_tables(db):
    existing = {t.name for t in db.tables.all()}
    for name, spec in TABLES.items():
        full = PREFIX + name
        if full in existing:
            print(f"exists   {full}")
            continue
        attrs = {a: t for a, t, _ in spec["keys"]}
        kwargs = {
            "TableName": full,
            "KeySchema": [{"AttributeName": a, "KeyType": k} for a, _, k in spec["keys"]],
            "BillingMode": "PAY_PER_REQUEST",
        }
        if "gsi" in spec:
            kwargs["GlobalSecondaryIndexes"] = []
            for index, attr in spec["gsi"]:
                attrs[attr] = "S"
                kwargs["GlobalSecondaryIndexes"].append({
                    "IndexName": index,
                    "KeySchema": [{"AttributeName": attr, "KeyType": "HASH"}],
                    "Projection": {"ProjectionType": "ALL"},
                })
        kwargs["AttributeDefinitions"] = [
            {"AttributeName": a, "AttributeType": t} for a, t in attrs.items()
        ]
        db.create_table(**kwargs)
        print(f"created  {full}")
    for name in TABLES:
        db.Table(PREFIX + name).wait_until_exists()


def seed(db):
    locations = db.Table(PREFIX + "Locations")
    for loc_id, name, address in LOCATIONS:
        locations.put_item(Item={"locationId": loc_id, "name": name, "address": address})
    rooms = db.Table(PREFIX + "Rooms")
    for room_id, loc_id, name, capacity, price in ROOMS:
        rooms.put_item(Item={"roomId": room_id, "locationId": loc_id, "name": name,
                             "capacity": capacity, "basePrice": Decimal(price)})
    print(f"seeded   {len(LOCATIONS)} locations, {len(ROOMS)} rooms")


if __name__ == "__main__":
    db = dynamodb()
    for attempt in range(30):  # wait for DynamoDB to be ready
        try:
            create_tables(db)
            break
        except Exception as e:
            if attempt == 29:
                raise
            print(f"waiting for DynamoDB... ({e.__class__.__name__})")
            time.sleep(2)
    seed(db)
