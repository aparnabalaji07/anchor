from collections import defaultdict

from fastapi import APIRouter

from app.db import pool

router = APIRouter()

WINDOW = "48 hours"

# Live boxes whose readings since their last "power on" are all "power off"
OUT_NOW_SQL = """
SELECT h.id, h.address, MIN(r.time)
FROM households h
JOIN readings r ON r.device_id = h.device_id
WHERE NOT h.simulated AND r.power_on = false
  AND r.time > COALESCE(
      (SELECT MAX(time) FROM readings r2 WHERE r2.device_id = h.device_id AND r2.power_on),
      '-infinity')
GROUP BY h.id, h.address
"""


@router.get("/notifications")
def notifications():
    items = []
    with pool.connection() as conn:
        for hid, address, since in conn.execute(OUT_NOW_SQL).fetchall():
            items.append({"id": f"out-{hid}-{since.timestamp():.0f}", "kind": "outage",
                          "title": "Power is out right now", "detail": address,
                          "time": since, "householdId": hid})

        # A box can send the same request many times, so count each household once
        calls = conn.execute(
            f"""SELECT DISTINCT ON (c.household_id) c.household_id, h.address, c.requested_at
                FROM call_requests c JOIN households h ON h.id = c.household_id
                WHERE c.requested_at > NOW() - INTERVAL '{WINDOW}'
                ORDER BY c.household_id, c.requested_at"""
        ).fetchall()
        # Requests that arrive in the same minute (a batch upload) become one notification
        by_minute = defaultdict(list)
        for hid, address, at in calls:
            by_minute[at.replace(second=0, microsecond=0)].append((hid, address, at))
        for minute, group in by_minute.items():
            if len(group) == 1:
                hid, address, at = group[0]
                items.append({"id": f"call-{hid}", "kind": "call", "title": "Asked for a call",
                              "detail": address, "time": at, "householdId": hid})
            else:
                items.append({"id": f"calls-{minute.timestamp():.0f}", "kind": "call",
                              "title": f"{len(group)} households asked for a call",
                              "detail": "Open the call queue to see them",
                              "time": max(g[2] for g in group), "householdId": None})

        for pid, hid, address, at in conn.execute(
            f"""SELECT p.id, p.household_id, h.address, p.uploaded_at
                FROM claim_photos p LEFT JOIN households h ON h.id = p.household_id
                WHERE p.uploaded_at > NOW() - INTERVAL '{WINDOW}'"""
        ).fetchall():
            items.append({"id": f"photo-{pid}", "kind": "photo", "title": "New claim photo",
                          "detail": address or "Unknown household", "time": at,
                          "householdId": hid})

        for rid, device_id, reason, at in conn.execute(
            f"""SELECT id, device_id, reason, received_at FROM rejected_messages
                WHERE received_at > NOW() - INTERVAL '{WINDOW}'"""
        ).fetchall():
            items.append({"id": f"rej-{rid}", "kind": "security",
                          "title": "Blocked a fake message",
                          "detail": f"{reason.replace('_', ' ')} from {device_id or 'unknown device'}",
                          "time": at, "householdId": None})

    items.sort(key=lambda i: i["time"], reverse=True)
    return items[:30]
