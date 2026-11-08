from fastapi import APIRouter, HTTPException, Request
from psycopg.types.json import Jsonb
from pydantic import ValidationError

from app.db import pool
from app.models import IngestBatch

router = APIRouter()


@router.post("/ingest")
async def ingest(request: Request):
    # Read the raw bytes first. Issue 8 will check the HMAC signature on these
    # exact bytes before anything else happens.
    raw_body = await request.body()

    try:
        batch = IngestBatch.model_validate_json(raw_body)
    except ValidationError as err:
        raise HTTPException(status_code=422, detail=err.errors()) from err

    rows = [
        (r.time, batch.device_id, r.power_on, Jsonb(r.sensors), r.counter, r.hash, r.prev_hash)
        for r in batch.readings
    ]

    with pool.connection() as conn, conn.cursor() as cur:
        cur.executemany(
            """INSERT INTO readings
               (time, device_id, power_on, sensors, counter, hash, prev_hash)
               VALUES (%s, %s, %s, %s, %s, %s, %s)
               ON CONFLICT (device_id, time) DO NOTHING""",
            rows,
        )

        if batch.call_requested:
            cur.execute(
                """INSERT INTO call_requests (household_id)
                   SELECT id FROM households WHERE device_id = %s""",
                (batch.device_id,),
            )

    return {"status": "ok", "saved": len(rows)}