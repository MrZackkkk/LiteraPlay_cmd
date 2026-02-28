import json
import re
from typing import Any

from literaplay.story_state import ChapterDef, StoryState


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


# ── Response validation against story state ──────────────────────────

_MAX_REPLY_CHARS = 1000
_FALLBACK_OPTIONS = [
    "Продължи...",
    "Разкажи ми повече.",
]


def validate_story_response(
    data: dict,
    state: StoryState | None = None,
    chapter: ChapterDef | None = None,
    is_last_chapter: bool = True,
) -> dict:
    """Sanitize / validate AI response against current story state.

    Returns a *new* dict with corrected values.
    """
    result = dict(data)  # shallow copy

    # --- reply ---
    reply = result.get("reply")
    if isinstance(reply, list):
        if not reply:
            result["reply"] = [{"character": "System", "text": "..."}]
    else:
        reply = reply or ""
        if not reply.strip():
            reply = "..."
        if len(reply) > _MAX_REPLY_CHARS:
            reply = reply[:_MAX_REPLY_CHARS].rsplit(" ", 1)[0] + "..."
        result["reply"] = reply

    # --- ended ---
    ended = result.get("ended", False)
    if ended and not is_last_chapter:
        # AI signalled end, but there are more chapters → chapter-end, not story-end
        result["ended"] = False
        result["_chapter_ended"] = True
    else:
        result["_chapter_ended"] = False

    # --- options ---
    options = result.get("options")
    if not isinstance(options, list):
        options = []
    if not result.get("ended") and not result.get("_chapter_ended") and len(options) == 0:
        options = list(_FALLBACK_OPTIONS)
    result["options"] = options

    return result
