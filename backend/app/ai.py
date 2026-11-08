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

BRIEF_PROMPT = (
    "You help insurance agents respond after a power outage. "
    "Write 2 to 3 short, plain sentences summarizing the outage event for the agent: "
    "how big it was, who is most at risk, and how much outreach is left. "
    "Use only the facts given. Never invent details, names, places or numbers. "
    "If a fact is null, leave it out. Do not use bullet points, headings or markdown."
)


def ask_text(system_prompt: str, facts: dict, max_tokens: int, max_chars: int) -> str | None:
    """Returns the model's plain-text reply, or None if the AI call fails."""
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(facts, default=str)},
            ],
            max_tokens=max_tokens,
            temperature=0.3,
        )
    except OpenAIError:
        return None

    text = (response.choices[0].message.content or "").strip()
    return text[:max_chars] or None


def write_reason(facts: dict) -> str | None:
    """Returns a short reason, or None if the AI call fails."""
    return ask_text(REASON_PROMPT, facts, max_tokens=150, max_chars=400)


def write_brief(facts: dict) -> str | None:
    """Returns a 2 to 3 sentence event summary, or None if the AI call fails."""
    return ask_text(BRIEF_PROMPT, facts, max_tokens=1000, max_chars=700)


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