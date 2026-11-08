from fastapi import APIRouter

from app.db import pool

router = APIRouter()

# time_bucket is a TimescaleDB function: it groups readings into hourly buckets
TIMELINE_SQL = """
SELECT time_bucket('1 hour', time) AS bucket,
       COUNT(DISTINCT device_id) FILTER (WHERE power_on = false) AS without_power,
       AVG((sensors->>'room_temp')::float) AS avg_temp
FROM readings
WHERE time > NOW() - INTERVAL '36 hours'
GROUP BY bucket
ORDER BY bucket
"""


@router.get("/stats")
def get_stats():
    with pool.connection() as conn:
        timeline = conn.execute(TIMELINE_SQL).fetchall()
        rejected = conn.execute(
            """SELECT reason, COUNT(*) FROM rejected_messages
               WHERE received_at > NOW() - INTERVAL '24 hours'
               GROUP BY reason ORDER BY COUNT(*) DESC"""
        ).fetchall()

    return {
        "timeline": [
            {"time": b, "withoutPower": n, "avgTemp": round(t, 1) if t is not None else None}
            for b, n, t in timeline
        ],
        "rejected24h": sum(c for _, c in rejected),
        "rejectedByReason": {r: c for r, c in rejected},
    }
