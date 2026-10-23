"""User Authentication Service: register, login and token verification."""
import os
import re
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from botocore.exceptions import ClientError
from flask import Flask, jsonify, request

from db import table

PREFIX = "/api/auth"
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
TOKEN_HOURS = 1


def secret():
    return os.getenv("JWT_SECRET", "dev-secret-change-me")


def make_token(email, name):
    now = datetime.now(timezone.utc)
    payload = {"sub": email, "name": name, "iat": now,
               "exp": now + timedelta(hours=TOKEN_HOURS)}
    return jwt.encode(payload, secret(), algorithm="HS256")


def create_app():
    app = Flask(__name__)

    @app.get(f"{PREFIX}/health")
    def health():
        return jsonify(status="ok", service="auth")

    @app.post(f"{PREFIX}/register")
    def register():
        data = request.get_json(silent=True) or {}
        email = (data.get("email") or "").strip().lower()
        name = (data.get("name") or "").strip()
        password = data.get("password") or ""
        if not EMAIL_RE.match(email):
            return jsonify(error="A valid email is required"), 400
        if not name:
            return jsonify(error="Name is required"), 400
        if len(password) < 8:
            return jsonify(error="Password must be at least 8 characters"), 400

        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        try:
            table("Users").put_item(
                Item={"email": email, "name": name, "passwordHash": hashed,
                      "createdAt": datetime.now(timezone.utc).isoformat()},
                ConditionExpression="attribute_not_exists(email)",
            )
        except ClientError as e:
            if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
                return jsonify(error="An account with this email already exists"), 409
            raise
        return jsonify(token=make_token(email, name), email=email, name=name), 201

    @app.post(f"{PREFIX}/login")
    def login():
        data = request.get_json(silent=True) or {}
        email = (data.get("email") or "").strip().lower()
        password = data.get("password") or ""
        user = table("Users").get_item(Key={"email": email}).get("Item")
        if not user or not bcrypt.checkpw(password.encode(), user["passwordHash"].encode()):
            return jsonify(error="Invalid email or password"), 401
        return jsonify(token=make_token(email, user["name"]), email=email, name=user["name"])

    @app.get(f"{PREFIX}/verify")
    def verify():
        header = request.headers.get("Authorization", "")
        token = header[7:] if header.startswith("Bearer ") else ""
        try:
            claims = jwt.decode(token, secret(), algorithms=["HS256"])
        except jwt.PyJWTError:
            return jsonify(error="Invalid or expired token"), 401
        return jsonify(email=claims["sub"], name=claims.get("name"))

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
