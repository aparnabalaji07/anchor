import hashlib
import hmac
import os

from app.db import pool


def load_device_keys() -> dict[str, bytes]:
    """Reads DEVICE_SECRET_KEYS like 'box-001:abc123,box-002:def456'."""
    raw = os.getenv("DEVICE_SECRET_KEYS", "")
    keys = {}
    for pair in raw.split(","):
        if ":" in pair:
            device_id, secret = pair.strip().split(":", 1)
            keys[device_id] = secret.encode()
    return keys


DEVICE_KEYS = load_device_keys()


def signature_is_valid(device_id: str, raw_body: bytes, signature: str) -> bool:
    expected = hmac.new(DEVICE_KEYS[device_id], raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature.lower())


def log_rejection(device_id: str | None, reason: str) -> None:
    with pool.connection() as conn:
        conn.execute(
            "INSERT INTO rejected_messages (device_id, reason) VALUES (%s, %s)",
            (device_id, reason),
        )