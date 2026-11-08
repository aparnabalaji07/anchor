from typing import Literal

from fastapi import APIRouter, HTTPException
from psycopg.types.json import Jsonb
from pydantic import BaseModel, Field, ValidationError

from app.ai import ask_json
from app.auth import CurrentAgent
from app.db import pool
from app.households import household_summary
from app.verify import verify_device

router = APIRouter()

CLAIM_PROMPT = (
    "You help insurance agents prepare a first notice of loss after a power outage. "
    "You are given measured sensor facts, photo observations and customer details. "
    "Reply with JSON only, in this exact shape: "
    '{"summary": "2-3 plain sentences for the agent", '
    '"likely_damage": ["up to 3 short damage types"], '
    '"questions": ["up to 4 short questions the agent should ask"]}. '
    "Only suggest damage the facts support, such as frozen pipes from very low "
    "temperatures or spoiled food from long outages. Never invent facts. "
    "Questions should cover only what sensors cannot know, like which rooms had water "
    "or whether the customer stayed somewhere else. Never ask about outage length or "
    "indoor temperature, since those are already measured."
)


class AiClaimPart(BaseModel):
    summary: str
    likely_damage: list[str] = Field(default_factory=list)
    questions: list[str] = Field(default_factory=list)


def field(name, value, source, evidence=None):
    return {"name": name, "value": value, "source": source, "evidence": evidence}


@router.post("/households/{household_id}/claim-draft")
def create_claim_draft(household_id: int):
    s = household_summary(household_id)
    integrity = verify_device(s["device_id"])

    # 1. Measured facts come straight from the database, never from the AI
    fields = [
        field("Cause of loss", "Power outage", "measured", "Box detected loss of power"),
        field("Date of loss",
              s["outage_start"].date().isoformat() if s["outage_start"] else None,
              "measured"),
        field("Outage duration", f'{s["outage_hours"]} hours', "measured"),
        field("Lowest indoor temperature",
              f'{s["min_temp"]:.0f}°F' if s["min_temp"] is not None else None,
              "measured"),
        field("Hours below 55°F", s["cold_hours"], "measured"),
        field("Evidence integrity", integrity["status"], "measured",
              f'{integrity["readings_checked"]} readings checked'),
    ]

    photo_facts = []  # filled in once the Gemini photo pipeline exists

    # 2. The AI writes the summary, likely damage and questions
    ai_input = {
        "measured": {k: s[k] for k in ("outage_hours", "min_temp", "cold_hours")},
        "photo_observations": photo_facts,
        "photo_consent": s["photo_consent"],
        "asked_for_call": s["call_requested"],
    }
    raw = ask_json(CLAIM_PROMPT, ai_input)
    try:
        ai_part = AiClaimPart.model_validate(raw) if raw else None
    except ValidationError:
        ai_part = None

    if ai_part:
        for damage in ai_part.likely_damage[:3]:
            fields.append(field("Possible damage", damage, "needs_confirmation"))
        summary, questions, ai_used = ai_part.summary, ai_part.questions[:4], True
    else:
        summary = "AI summary unavailable. Review the measured facts below."
        questions = ["Was there any damage to the home?",
                     "Did you need to stay somewhere else during the outage?"]
        ai_used = False

    draft = {"summary": summary, "fields": fields, "questions": questions,
             "ai_used": ai_used}

    with pool.connection() as conn:
        draft_id = conn.execute(
            "INSERT INTO claim_drafts (household_id, draft) VALUES (%s, %s) RETURNING id",
            (household_id, Jsonb(draft)),
        ).fetchone()[0]

    return {"id": draft_id, "household_id": household_id, "status": "pending_review", **draft}


@router.get("/households/{household_id}/claim-draft")
def latest_claim_draft(household_id: int):
    with pool.connection() as conn:
        row = conn.execute(
            """SELECT id, draft, status, reviewed_by, created_at FROM claim_drafts
               WHERE household_id = %s ORDER BY id DESC LIMIT 1""",
            (household_id,),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="no claim draft yet")
    draft_id, draft, status, reviewed_by, created_at = row
    return {"id": draft_id, "household_id": household_id, "status": status,
            "reviewed_by": reviewed_by, "created_at": created_at, **draft}


class ClaimReview(BaseModel):
    status: Literal["approved", "rejected"]
    fields: list[dict] | None = None  # the agent's edited fields, if any


@router.patch("/claim-drafts/{draft_id}")
def review_claim_draft(draft_id: int, review: ClaimReview, agent: CurrentAgent):
    # The reviewer's name comes from their token, never from the request body
    reviewed_by = agent["name"]
    with pool.connection() as conn:
        row = conn.execute(
            "SELECT draft FROM claim_drafts WHERE id = %s", (draft_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="claim draft not found")
        draft = row[0]
        if review.fields is not None:
            draft["fields"] = review.fields
        conn.execute(
            """UPDATE claim_drafts
               SET status = %s, reviewed_by = %s, reviewed_at = NOW(), draft = %s
               WHERE id = %s""",
            (review.status, reviewed_by, Jsonb(draft), draft_id),
        )
    return {"id": draft_id, "status": review.status, "reviewed_by": reviewed_by}