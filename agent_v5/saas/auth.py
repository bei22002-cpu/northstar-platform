"""Authentication — JWT token management for the SaaS platform."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from base64 import urlsafe_b64decode, urlsafe_b64encode
from typing import Optional


_SECRET = os.getenv("JWT_SECRET") or os.urandom(32).hex()
_EXPIRY = 86400 * 7  # 7 days


def _b64encode(data: bytes) -> str:
    return urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64decode(data: str) -> bytes:
    padding = 4 - len(data) % 4
    if padding != 4:
        data += "=" * padding
    return urlsafe_b64decode(data)


def create_token(user_id: int, email: str) -> str:
    """Create a simple JWT-like token."""
    header = _b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    payload_data = {
        "user_id": user_id,
        "email": email,
        "exp": time.time() + _EXPIRY,
    }
    payload = _b64encode(json.dumps(payload_data).encode())
    signature = hmac.new(
        _SECRET.encode(), f"{header}.{payload}".encode(), hashlib.sha256
    ).hexdigest()
    return f"{header}.{payload}.{signature}"


def verify_token(token: str) -> Optional[dict]:
    """Verify a token and return its payload, or None if invalid."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None

        header, payload, signature = parts
        expected_sig = hmac.new(
            _SECRET.encode(), f"{header}.{payload}".encode(), hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(signature, expected_sig):
            return None

        payload_data = json.loads(_b64decode(payload))
        if payload_data.get("exp", 0) < time.time():
            return None

        return payload_data
    except Exception:
        return None
