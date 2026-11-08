import hashlib
from datetime import UTC

from app.db import pool

GENESIS_HASH = "0" * 64


def expected_hash(device_id, time, counter, power_on, prev_hash):
    """Must match docs/message-format.md exactly."""
    t = time.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    power = 1 if power_on is None else int(power_on)
    return hashlib.sha256(
        f"{device_id}|{t}|{counter}|{power}|{prev_hash}".encode()
    ).hexdigest()


def verify_device(device_id: str) -> dict:
    with pool.connection() as conn:
        rows = conn.execute(
            """SELECT time, counter, power_on, hash, prev_hash
               FROM readings WHERE device_id = %s ORDER BY counter""",
            (device_id,),
        ).fetchall()

    if not rows:
        return {"status": "no_data", "readings_checked": 0,
                "first_bad_counter": None, "reason": None}

    previous = GENESIS_HASH
    for time, counter, power_on, stored_hash, prev_hash in rows:
        if prev_hash != previous:
            return {"status": "tampered", "readings_checked": len(rows),
                    "first_bad_counter": counter, "reason": "chain_broken"}
        if expected_hash(device_id, time, counter, power_on, prev_hash) != stored_hash:
            return {"status": "tampered", "readings_checked": len(rows),
                    "first_bad_counter": counter, "reason": "data_changed"}
        previous = stored_hash

    return {"status": "verified", "readings_checked": len(rows),
            "first_bad_counter": None, "reason": None}