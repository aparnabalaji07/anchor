import json
import os

from openai import OpenAI, OpenAIError

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