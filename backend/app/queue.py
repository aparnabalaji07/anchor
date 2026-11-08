from fastapi import APIRouter

from app.db import pool
from app.scoring import score_household

router = APIRouter()

QUEUE_SQL = """
WITH r AS (
    SELECT device_id, power_on,
           (sensors->>'room_temp')::float AS temp,
           LEAD(time) OVER (PARTITION BY device_id ORDER BY time) - time AS duration
    FROM readings
),
s AS (
    SELECT device_id,
           EXTRACT(EPOCH FROM SUM(duration) FILTER (WHERE power_on = false)) / 3600 AS outage_hours,
           MIN(temp) AS min_temp
    FROM r GROUP BY device_id
)
SELECT h.id, h.device_id, h.address, h.lat, h.lng,
       h.lives_alone, h.medical_device, h.mobility_limits, h.photo_consent,
       h.ai_reason,
       COALESCE(cs.status, 'not_contacted') AS status,
       EXISTS (SELECT 1 FROM call_requests c WHERE c.household_id = h.id) AS call_requested,
       COALESCE(s.outage_hours, 0) AS outage_hours,
       s.min_temp
FROM households h
LEFT JOIN s ON s.device_id = h.device_id
LEFT JOIN contact_status cs ON cs.household_id = h.id
"""


def build_queue():
    with pool.connection() as conn:
        cur = conn.execute(QUEUE_SQL)
        columns = [c.name for c in cur.description]
        households = [dict(zip(columns, row, strict=True)) for row in cur.fetchall()]

    results = []
    for h in households:
        h["outage_hours"] = round(float(h["outage_hours"]), 1)
        score, reasons = score_household(h)
        results.append({
            "id": h["id"],
            "deviceId": h["device_id"],
            "address": h["address"],
            "lat": h["lat"],
            "lng": h["lng"],
            "score": score,
            "reason": h["ai_reason"] or (". ".join(reasons) + "."),
            "ruleReasons": reasons,
            "aiReason": h["ai_reason"] is not None,
            "status": h["status"],
            "callRequested": h["call_requested"],
            "photoConsent": h["photo_consent"],
            "livesAlone": h["lives_alone"],
            "medicalDevice": h["medical_device"],
            "mobilityLimits": h["mobility_limits"],
            "summary": {
                "outageHours": h["outage_hours"],
                "minTemp": h["min_temp"],
            },
        })

    # Resolved households go to the bottom, everyone else by score
    results.sort(key=lambda x: (x["status"] == "resolved", -x["score"]))
    for i, item in enumerate(results, start=1):
        item["rank"] = i
    return results


@router.get("/queue")
def get_queue():
    return build_queue()