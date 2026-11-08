import hashlib
from datetime import datetime, timedelta

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request
from fastapi.responses import Response

from app.db import pool
from app.households import get_device_id
from app.security import DEVICE_KEYS, log_rejection, signature_is_valid
from app.vision import analyze_photo

MAX_PHOTO_BYTES = 2 * 1024 * 1024

# Boxes sign photos with HMAC, so this router does not use agent login
device_router = APIRouter()

# Viewing photos needs a signed-in agent (added in main.py)
router = APIRouter()


def reject(device_id: str | None, reason: str):
    log_rejection(device_id, reason)
    raise HTTPException(status_code=401, detail=reason)


def parse_utc(value: str) -> datetime:
    try:
        taken_at = datetime.fromisoformat(value)
    except ValueError:
        raise HTTPException(status_code=422, detail="X-Taken-At must be ISO 8601") from None
    if taken_at.utcoffset() != timedelta(0):
        raise HTTPException(status_code=422, detail="X-Taken-At must be in UTC")
    return taken_at


@device_router.post("/photos")
async def upload_photo(
    request: Request,
    background: BackgroundTasks,
    x_device_id: str = Header(...),
    x_taken_at: str = Header(...),
    x_signature: str = Header(...),
    content_type: str = Header(""),
):
    # Check the declared size before reading the body
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > MAX_PHOTO_BYTES:
        raise HTTPException(status_code=413, detail="Photo is larger than 2 MB")
    image = await request.body()
    if len(image) > MAX_PHOTO_BYTES:
        raise HTTPException(status_code=413, detail="Photo is larger than 2 MB")

    if x_device_id not in DEVICE_KEYS:
        reject(x_device_id, "unknown_device")

    # The signature covers the time and the image, so neither can be swapped later
    if not signature_is_valid(x_device_id, x_taken_at.encode() + b"\n" + image, x_signature):
        reject(x_device_id, "bad_signature")

    taken_at = parse_utc(x_taken_at)

    # JPEG files start with FF D8 FF
    if content_type.split(";")[0].strip().lower() != "image/jpeg" or not image.startswith(b"\xff\xd8\xff"):
        raise HTTPException(status_code=415, detail="Only JPEG photos are accepted")

    sha256 = hashlib.sha256(image).hexdigest()
    with pool.connection() as conn:
        row = conn.execute(
            """INSERT INTO claim_photos (household_id, device_id, taken_at, sha256, image)
               VALUES ((SELECT id FROM households WHERE device_id = %s), %s, %s, %s, %s)
               ON CONFLICT (sha256) DO NOTHING
               RETURNING id""",
            (x_device_id, x_device_id, taken_at, sha256, image),
        ).fetchone()
    if row is None:
        log_rejection(x_device_id, "duplicate_photo")
        raise HTTPException(status_code=409, detail="duplicate_photo")

    # Analysis can take several seconds, so it runs after the response is sent
    background.add_task(analyze_photo, row[0])
    return {"id": row[0], "sha256": sha256}


@router.get("/households/{household_id}/photos")
def list_photos(household_id: int):
    get_device_id(household_id)  # 404 for an unknown household
    with pool.connection() as conn:
        rows = conn.execute(
            # verified: the stored bytes still hash to the hash saved at upload
            """SELECT id, taken_at, sha256, analysis, analysis_status,
                      encode(sha256(image), 'hex') = sha256 AS verified
               FROM claim_photos WHERE household_id = %s ORDER BY taken_at DESC""",
            (household_id,),
        ).fetchall()
    return [
        {"id": r[0], "taken_at": r[1], "sha256": r[2], "analysis": r[3],
         "analysis_status": r[4], "verified": r[5]}
        for r in rows
    ]


@router.get("/photos/{photo_id}/image")
def photo_image(photo_id: int):
    with pool.connection() as conn:
        row = conn.execute(
            "SELECT image, content_type FROM claim_photos WHERE id = %s", (photo_id,)
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="photo not found")
    return Response(content=bytes(row[0]), media_type=row[1],
                    headers={"Cache-Control": "private, max-age=3600"})


@router.post("/photos/{photo_id}/analyze")
def reanalyze_photo(photo_id: int, background: BackgroundTasks):
    with pool.connection() as conn:
        row = conn.execute(
            """UPDATE claim_photos SET analysis_status = 'pending'
               WHERE id = %s RETURNING id""",
            (photo_id,),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="photo not found")
    background.add_task(analyze_photo, photo_id)
    return {"id": photo_id, "analysis_status": "pending"}
