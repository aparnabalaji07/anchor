from fastapi import APIRouter

from app.db import pool
from app.verify import verify_all

router = APIRouter()


@router.get("/integrity")
def integrity():
    chains = verify_all()
    with pool.connection() as conn:
        households = conn.execute(
            """SELECT h.id, h.device_id, h.address, h.simulated,
                      (SELECT MAX(time) FROM readings r WHERE r.device_id = h.device_id)
               FROM households h"""
        ).fetchall()
        # verified: the stored bytes still hash to the hash saved at upload
        photos = conn.execute(
            """SELECT COUNT(*), COUNT(*) FILTER (WHERE encode(sha256(image), 'hex') = sha256)
               FROM claim_photos"""
        ).fetchone()
        rejected = conn.execute(
            """SELECT id, device_id, reason, received_at FROM rejected_messages
               ORDER BY received_at DESC LIMIT 50"""
        ).fetchall()
        rejected_24h = conn.execute(
            "SELECT COUNT(*) FROM rejected_messages WHERE received_at > NOW() - INTERVAL '24 hours'"
        ).fetchone()[0]

    empty = {"status": "no_data", "readings_checked": 0, "first_bad_counter": None, "reason": None}
    items = []
    for hid, device_id, address, simulated, last_reading in households:
        c = chains.get(device_id, empty)
        items.append({
            "id": hid, "deviceId": device_id, "address": address, "simulated": simulated,
            "status": c["status"], "readingsChecked": c["readings_checked"],
            "firstBadCounter": c["first_bad_counter"], "reason": c["reason"],
            "lastReading": last_reading,
        })
    # Problems first, then live boxes, then the rest
    order = {"tampered": 0, "no_data": 1, "verified": 2}
    items.sort(key=lambda h: (order[h["status"]], h["simulated"], h["address"]))

    return {
        "households": items,
        "photos": {"total": photos[0], "verified": photos[1], "changed": photos[0] - photos[1]},
        "rejected24h": rejected_24h,
        "rejected": [
            {"id": r[0], "deviceId": r[1], "reason": r[2], "receivedAt": r[3]} for r in rejected
        ],
    }
