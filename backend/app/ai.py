import json
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI, OpenAIError

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

client = OpenAI(
    base_url=os.getenv("AI_BASE_URL"),
    api_key=os.getenv("AI_API_KEY"),
    timeout=20,
    max_retries=1,
)
MODEL = os.getenv("AI_MODEL")

REASON_PROMPT = (
    "You help insurance agents decide which customers to call first after a power outage. "
    "Write one or two short, plain sentences explaining why this household should be called. "
    "Use only the facts given. Never invent details. Do not use bullet points."
)


def write_reason(facts: dict) -> str | None:
    """Returns a short reason, or None if the AI call fails."""
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": REASON_PROMPT},
                {"role": "user", "content": json.dumps(facts, default=str)},
            ],
            max_tokens=150,
            temperature=0.3,
        )
    except OpenAIError:
        return None

    text = (response.choices[0].message.content or "").strip()
    return text[:400] or None


def ask_json(system_prompt: str, user_content: dict) -> dict | None:
    """Asks the model for JSON. Returns None if the call fails or the reply is not valid JSON."""
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(user_content, default=str)},
            ],
            max_tokens=600,
            temperature=0.2,
        )
    except OpenAIError:
        return None

    text = (response.choices[0].message.content or "").strip()
    # Some models wrap JSON in ```json fences
    if text.startswith("```"):
        text = text.strip("`").removeprefix("json").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None