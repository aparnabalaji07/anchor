from fastapi import APIRouter

from app.ai import write_reason
from app.db import pool
from app.queue import build_queue

router = APIRouter(prefix="/ai")


@router.post("/reasons")
def generate_reasons(limit: int = 15):
    queue = [h for h in build_queue() if h["status"] != "resolved"][:limit]
    written = 0
    for h in queue:
        facts = {
            "outage_hours": h["summary"]["outageHours"],
            "lowest_indoor_temp_f": h["summary"]["minTemp"],
            "lives_alone": h["livesAlone"],
            "medical_device": h["medicalDevice"],
            "mobility_limits": h["mobilityLimits"],
            "asked_for_call": h["callRequested"],
            "rule_based_reasons": h["ruleReasons"],
        }
        reason = write_reason(facts)
        if reason:
            with pool.connection() as conn:
                conn.execute(
                    "UPDATE households SET ai_reason = %s WHERE id = %s", (reason, h["id"])
                )
            written += 1
    return {"requested": len(queue), "written": written}