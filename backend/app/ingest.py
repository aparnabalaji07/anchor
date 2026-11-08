from fastapi import APIRouter, Header, HTTPException, Request
from psycopg.types.json import Jsonb
from pydantic import ValidationError

from app.db import pool
from app.models import IngestBatch
from app.security import DEVICE_KEYS, log_rejection, signature_is_valid

router = APIRouter()


def reject(device_id: str | None, reason: str):
    log_rejection(device_id, reason)
    raise HTTPException(status_code=401, detail=reason)


@router.post("/ingest")
async def ingest(
    request: Request,
    x_device_id: str = Header(...),
    x_signature: str = Header(...),
):
    raw_body = await request.body()

    if x_device_id not in DEVICE_KEYS:
        reject(x_device_id, "unknown_device")

    if not signature_is_valid(x_device_id, raw_body, x_signature):
        reject(x_device_id, "bad_signature")

    try:
        batch = IngestBatch.model_validate_json(raw_body)
    except ValidationError as err:
        raise HTTPException(status_code=422, detail=err.errors()) from err

    if batch.device_id != x_device_id:
        reject(x_device_id, "device_mismatch")

    counters = [r.counter for r in batch.readings]
    if counters != sorted(set(counters)):
        reject(x_device_id, "counters_not_increasing")

    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT COALESCE(MAX(counter), 0) FROM readings WHERE device_id = %s",
            (batch.device_id,),
        )
        last_counter = cur.fetchone()[0]
        if counters[0] <= last_counter:
            reject(x_device_id, "replayed_counter")

        rows = [
            (r.time, batch.device_id, r.power_on, Jsonb(r.sensors),
             r.counter, r.hash, r.prev_hash)
            for r in batch.readings
        ]
        cur.executemany(
            """INSERT INTO readings
               (time, device_id, power_on, sensors, counter, hash, prev_hash)
               VALUES (%s, %s, %s, %s, %s, %s, %s)
               ON CONFLICT (device_id, time) DO NOTHING""",
            rows,
        )
        cur.execute(
            "UPDATE households SET photo_consent = %s WHERE device_id = %s",
            (batch.photo_consent, batch.device_id),
        )
        if batch.call_requested:
            cur.execute(
                """INSERT INTO call_requests (household_id)
                   SELECT id FROM households WHERE device_id = %s""",
                (batch.device_id,),
            )

    return {"status": "ok", "saved": len(rows)}