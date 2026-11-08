"""Describes claim photos with Gemini through its OpenAI-compatible API."""

import base64
import json
import os
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from openai import OpenAI, OpenAIError
from psycopg.types.json import Jsonb
from pydantic import BaseModel, ValidationError

from app.db import pool

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

client = OpenAI(
    base_url=os.getenv("GEMINI_BASE_URL") or "https://generativelanguage.googleapis.com/v1beta/openai/",
    api_key=os.getenv("GEMINI_API_KEY") or "missing",
    timeout=30,
    max_retries=1,
)
MODEL = os.getenv("GEMINI_MODEL") or "gemini-3.5-flash"

PHOTO_PROMPT = (
    "You help an insurance agent review a claim photo taken after a power outage. "
    "Reply with JSON only, in this exact shape: "
    '{"description": "one plain sentence", '
    '"damage": ["short damage types visible, empty list if none"], '
    '"location": "room or area if visible, else null", '
    '"severity": "none|minor|moderate|severe", '
    '"items": ["affected items visible"], '
    '"confidence": "low|medium|high"}. '
    "Describe only what is visible. Never guess at causes, costs or coverage. "
    "Do not identify or describe people."
)


class PhotoAnalysis(BaseModel):
    description: str
    damage: list[str]
    location: str | None
    severity: Literal["none", "minor", "moderate", "severe"]
    items: list[str]
    confidence: Literal["low", "medium", "high"]


def describe_image(image: bytes, content_type: str) -> PhotoAnalysis | None:
    """Returns the validated analysis, or None if the call or the reply is bad."""
    data_url = f"data:{content_type};base64,{base64.b64encode(image).decode()}"
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": PHOTO_PROMPT},
                {"role": "user", "content": [
                    {"type": "text", "text": "Describe this claim photo."},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ]},
            ],
            temperature=0.2,
        )
    except OpenAIError as err:
        print(f"[vision] Gemini call failed: {err}")
        return None

    text = (response.choices[0].message.content or "").strip()
    # The reply is sometimes wrapped in ```json fences
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end < start:
        print("[vision] Gemini reply had no JSON")
        return None
    try:
        return PhotoAnalysis.model_validate(json.loads(text[start:end + 1]))
    except (json.JSONDecodeError, ValidationError) as err:
        print(f"[vision] Gemini reply did not match the expected shape: {err}")
        return None


def analyze_photo(photo_id: int) -> None:
    """Analyzes one stored photo and saves the result. Safe to run in a background task."""
    with pool.connection() as conn:
        row = conn.execute(
            "SELECT image, content_type FROM claim_photos WHERE id = %s", (photo_id,)
        ).fetchone()
    if row is None:
        return

    result = describe_image(bytes(row[0]), row[1])
    with pool.connection() as conn:
        if result is None:
            conn.execute(
                "UPDATE claim_photos SET analysis_status = 'failed' WHERE id = %s", (photo_id,)
            )
        else:
            conn.execute(
                "UPDATE claim_photos SET analysis = %s, analysis_status = 'done' WHERE id = %s",
                (Jsonb(result.model_dump()), photo_id),
            )
