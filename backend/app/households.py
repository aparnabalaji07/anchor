from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.db import pool
from app.verify import verify_device

router = APIRouter(prefix="/households")


def get_device_id(household_id: int) -> str:
    with pool.connection() as conn:
        row = conn.execute(
            "SELECT device_id FROM households WHERE id = %s", (household_id,)
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="household not found")
    return row[0]


@router.get("/{household_id}/verify")
def verify_household(household_id: int):
    device_id = get_device_id(household_id)
    return {"household_id": household_id, "device_id": device_id,
            **verify_device(device_id)}


SUMMARY_SQL = """
WITH r AS (
    SELECT
        time,
        power_on,
        (sensors->>'room_temp')::float AS temp,
        LEAD(time) OVER (ORDER BY time) - time AS duration
    FROM readings
    WHERE device_id = %s
)
SELECT
    MIN(time) FILTER (WHERE power_on = false)                       AS outage_start,
    MAX(time + duration) FILTER (WHERE power_on = false)            AS outage_end,
    EXTRACT(EPOCH FROM SUM(duration) FILTER (WHERE power_on = false)) / 3600
                                                                    AS outage_hours,
    MIN(temp)                                                       AS min_temp,
    EXTRACT(EPOCH FROM SUM(duration) FILTER (WHERE temp < 55)) / 3600
                                                                    AS cold_hours,
    COUNT(*)                                                        AS readings
FROM r
"""


@router.get("/{household_id}/summary")
def household_summary(household_id: int):
    device_id = get_device_id(household_id)
    with pool.connection() as conn:
        row = conn.execute(SUMMARY_SQL, (device_id,)).fetchone()
        photo_consent = conn.execute(
            "SELECT photo_consent FROM households WHERE device_id = %s",
            (device_id,),
        ).fetchone()[0]
        call_requested = conn.execute(
            "SELECT EXISTS (SELECT 1 FROM call_requests WHERE household_id = %s)",
            (household_id,),
        ).fetchone()[0]

    outage_start, outage_end, outage_hours, min_temp, cold_hours, readings = row
    return {
        "household_id": household_id,
        "device_id": device_id,
        "outage_start": outage_start,
        "outage_end": outage_end,
        "outage_hours": round(float(outage_hours or 0), 1),
        "min_temp": min_temp,
        "cold_hours": round(float(cold_hours or 0), 1),
        "call_requested": call_requested,
        "photo_consent": photo_consent,
        "readings": readings,
    }

class StatusUpdate(BaseModel):
    status: Literal["not_contacted", "contacted", "needs_follow_up", "resolved"]
    updated_by: str = Field(min_length=1, description="Name of the agent making the change")


@router.patch("/{household_id}/status")
def update_status(household_id: int, update: StatusUpdate):
    get_device_id(household_id)  # 404 if the household does not exist
    with pool.connection() as conn:
        conn.execute(
            """INSERT INTO contact_status (household_id, status, updated_by, updated_at)
               VALUES (%s, %s, %s, NOW())
               ON CONFLICT (household_id)
               DO UPDATE SET status = EXCLUDED.status,
                             updated_by = EXCLUDED.updated_by,
                             updated_at = NOW()""",
            (household_id, update.status, update.updated_by),
        )
    return {"household_id": household_id, "status": update.status,
            "updated_by": update.updated_by}