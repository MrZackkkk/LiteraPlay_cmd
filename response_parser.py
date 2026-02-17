import json
import re
from typing import Any


def parse_ai_json_response(response_text: str) -> dict[str, Any] | None:
    """Parse an AI response expected to contain a JSON object.

    The function supports plain JSON, fenced code blocks, and extracting the
    first JSON object embedded inside free-form text.
    """
    if not response_text:
        return None

    parsed = _try_parse(response_text)
    if isinstance(parsed, dict):
        return parsed

    cleaned_text = _strip_markdown_fence(response_text)
    parsed = _try_parse(cleaned_text)
    if isinstance(parsed, dict):
        return parsed

    json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
    if not json_match:
        return None

    parsed = _try_parse(json_match.group(0))
    return parsed if isinstance(parsed, dict) else None


def _strip_markdown_fence(text: str) -> str:
    cleaned_text = text.strip()
    if cleaned_text.startswith("```json"):
        cleaned_text = cleaned_text[7:]
    elif cleaned_text.startswith("```"):
        cleaned_text = cleaned_text[3:]

    if cleaned_text.endswith("```"):
        cleaned_text = cleaned_text[:-3]

    return cleaned_text.strip()


def _try_parse(text: str) -> Any:
    try:
        return json.loads(text)
    except (TypeError, json.JSONDecodeError):
        return None

