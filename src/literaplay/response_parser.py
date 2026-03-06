import json
import logging
import re
from typing import Any

from literaplay.story_state import ChapterDef, StoryState

_log = logging.getLogger(__name__)

_MAX_KEY_EVENT_CHARS = 120
_MAX_CHARACTERS_PRESENT = 8
_MAX_ACTIVE_PROPS = 10
_MAX_PROP_CHARS = 60
# Minimum prefix length used for fuzzy token matching (handles inflected Bulgarian words)
_STEM_PREFIX_LEN = 4

# Pre-compiled pattern for stripping non-word characters when comparing location tokens
_NON_WORD_RE = re.compile(r"[^\w\s]")


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

    # Try to extract the first balanced JSON object from the text
    start = response_text.find("{")
    if start == -1:
        return None
    depth = 0
    for i in range(start, len(response_text)):
        ch = response_text[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                parsed = _try_parse(response_text[start : i + 1])
                return parsed if isinstance(parsed, dict) else None
    return None


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

    # --- location drift ---
    if chapter is not None and "location" in result:
        ai_location = result["location"]
        if isinstance(ai_location, str):
            # Extract tokens longer than 2 chars, then compare by _STEM_PREFIX_LEN-char prefix
            # to handle Bulgarian inflections (e.g. "Оборът" vs "обора" both share "обор").
            def _stem_set(text: str) -> set[str]:
                return {
                    w.lower()[:_STEM_PREFIX_LEN]
                    for w in _NON_WORD_RE.sub("", text).split()
                    if len(w) > 2
                }

            setting_stems = _stem_set(chapter.setting)
            location_stems = _stem_set(ai_location)
            if not setting_stems.intersection(location_stems):
                _log.warning(
                    "Location drift detected: AI returned %r but chapter setting is %r — reverting.",
                    ai_location,
                    chapter.setting,
                )
                result["location"] = chapter.setting

    # --- key_event dedup and cap ---
    if "key_event" in result:
        event = result["key_event"]
        if isinstance(event, str):
            event = event[:_MAX_KEY_EVENT_CHARS]
            result["key_event"] = event
            if state is not None and event in state.key_events:
                del result["key_event"]
        else:
            del result["key_event"]

    # --- characters_present ---
    if "characters_present" in result:
        cp = result["characters_present"]
        if not isinstance(cp, list) or not all(isinstance(x, str) for x in cp):
            del result["characters_present"]
        else:
            result["characters_present"] = cp[:_MAX_CHARACTERS_PRESENT]

    # --- trust_level ---
    if "trust_level" in result:
        tl = result["trust_level"]
        if not isinstance(tl, int) or not (-3 <= tl <= 3):
            del result["trust_level"]

    # --- active_props ---
    if "active_props" in result:
        ap = result["active_props"]
        if not isinstance(ap, list) or not all(isinstance(x, str) for x in ap):
            del result["active_props"]
        else:
            result["active_props"] = [p[:_MAX_PROP_CHARS] for p in ap][:_MAX_ACTIVE_PROPS]

    return result
