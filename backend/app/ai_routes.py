from fastapi import APIRouter, HTTPException

from app.ai import write_brief, write_reason
from app.db import pool
from app.queue import build_queue
from app.stats import ZIPS_SQL

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


def event_facts() -> dict:
    """Measured facts about the outage, counted the same way as the overview page."""
    queue = build_queue()
    affected = [h for h in queue if h["summary"]["outageHours"] > 0]
    temps = [h["summary"]["minTemp"] for h in affected if h["summary"]["minTemp"] is not None]
    with pool.connection() as conn:
        top_zip = conn.execute(ZIPS_SQL + " LIMIT 1").fetchone()

    return {
        "households_affected": len(affected),
        "critical_still_open": sum(1 for h in queue if h["score"] >= 70 and h["status"] != "resolved"),
        "affected_not_yet_reached": sum(1 for h in affected if h["status"] == "not_contacted"),
        "longest_outage_hours": max((h["summary"]["outageHours"] for h in affected), default=None),
        "lowest_indoor_temp_f": round(min(temps), 1) if temps else None,
        "hardest_hit_zip": top_zip[0] if top_zip else None,
        "hardest_hit_zip_households": top_zip[1] if top_zip else None,
        "households_asked_for_call": sum(1 for h in queue if h["callRequested"]),
        "affected_with_medical_device": sum(1 for h in affected if h["medicalDevice"]),
    }


def fallback_brief(f: dict) -> str:
    """Plain summary built from the facts, used when the AI call fails."""
    if not f["households_affected"]:
        return "No households have lost power so far."
    parts = [
        f"{f['households_affected']} households lost power.",
        f"{f['critical_still_open']} are critical and {f['affected_not_yet_reached']} have not been reached yet."
    ]
    detail = []
    if f["longest_outage_hours"] is not None:
        detail.append(f"the longest outage lasted {f['longest_outage_hours']} hours")
    if f["lowest_indoor_temp_f"] is not None:
        detail.append(f"the lowest indoor temperature was {f['lowest_indoor_temp_f']}°F")
    if detail:
        sentence = " and ".join(detail)
        parts.append(sentence[0].upper() + sentence[1:] + ".")
    if f["hardest_hit_zip"]:
        parts.append(
            f"{f['hardest_hit_zip']} was hit hardest with {f['hardest_hit_zip_households']} homes; "
            f"{f['households_asked_for_call']} asked for a call and "
            f"{f['affected_with_medical_device']} rely on a medical device."
        )
    return " ".join(parts)


@router.post("/brief")
def create_brief():
    facts = event_facts()
    brief = write_brief(facts) or fallback_brief(facts)
    with pool.connection() as conn:
        row = conn.execute(
            "INSERT INTO ai_briefs (brief) VALUES (%s) RETURNING id, brief, created_at", (brief,)
        ).fetchone()
    return {"id": row[0], "brief": row[1], "createdAt": row[2]}


@router.get("/brief")
def latest_brief():
    with pool.connection() as conn:
        row = conn.execute(
            "SELECT id, brief, created_at FROM ai_briefs ORDER BY created_at DESC, id DESC LIMIT 1"
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="No brief yet")
    return {"id": row[0], "brief": row[1], "createdAt": row[2]}
