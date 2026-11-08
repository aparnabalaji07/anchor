from fastapi import APIRouter, HTTPException

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