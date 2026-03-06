"""Tests for response_parser module.

Covers parse_ai_json_response (including balanced-brace extraction)
and validate_story_response (including list-reply branch — T-02).
"""

import unittest

from literaplay.response_parser import parse_ai_json_response, validate_story_response
from literaplay.story_state import ChapterDef, StoryState


def _make_chapter(setting: str = "Оборът на Бай Марко") -> ChapterDef:
    return ChapterDef(
        id="ch_test",
        title="Test Chapter",
        setting=setting,
        character_mood="suspicious",
        plot_summary="A tense meeting.",
        end_condition="The stranger leaves.",
        max_turns=10,
    )


def _make_state(key_events: list[str] | None = None) -> StoryState:
    return StoryState(work_key="test", key_events=key_events or [])


class TestResponseParser(unittest.TestCase):
    def test_parse_plain_json(self):
        parsed = parse_ai_json_response('{"reply":"hi","options":["a","b","c"]}')
        assert parsed is not None
        self.assertEqual(parsed["reply"], "hi")

    def test_parse_markdown_fenced_json(self):
        text = """```json
{"reply":"hello","options":["1","2","3"]}
```"""
        parsed = parse_ai_json_response(text)
        assert parsed is not None
        self.assertEqual(parsed["reply"], "hello")

    def test_parse_embedded_json(self):
        text = 'Model answer: {"reply":"ok","options":[]} End.'
        parsed = parse_ai_json_response(text)
        assert parsed is not None
        self.assertEqual(parsed["reply"], "ok")

    def test_parse_invalid_returns_none(self):
        self.assertIsNone(parse_ai_json_response("not json"))

    def test_parse_empty_returns_none(self):
        self.assertIsNone(parse_ai_json_response(""))

    def test_parse_nested_json(self):
        """Balanced-brace extraction handles nested objects."""
        text = 'prefix {"reply":"ok","meta":{"a":1}} suffix'
        parsed = parse_ai_json_response(text)
        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(parsed["reply"], "ok")
        self.assertEqual(parsed["meta"]["a"], 1)

    def test_parse_multiple_json_objects_returns_first(self):
        """When two JSON objects appear, the first balanced one is returned."""
        text = '{"reply":"first"} junk {"reply":"second"}'
        parsed = parse_ai_json_response(text)
        assert parsed is not None
        self.assertEqual(parsed["reply"], "first")


class TestValidateStoryResponse(unittest.TestCase):
    def test_empty_reply_gets_fallback(self):
        result = validate_story_response({"reply": "", "options": [], "ended": False})
        self.assertEqual(result["reply"], "...")

    def test_ended_on_non_last_chapter_becomes_chapter_ended(self):
        result = validate_story_response(
            {"reply": "bye", "options": [], "ended": True},
            is_last_chapter=False,
        )
        self.assertFalse(result["ended"])
        self.assertTrue(result["_chapter_ended"])

    def test_ended_on_last_chapter_stays_ended(self):
        result = validate_story_response(
            {"reply": "final", "options": [], "ended": True},
            is_last_chapter=True,
        )
        self.assertTrue(result["ended"])
        self.assertFalse(result["_chapter_ended"])

    def test_missing_options_get_fallback(self):
        result = validate_story_response(
            {"reply": "hello", "options": None, "ended": False},
            is_last_chapter=True,
        )
        self.assertIsInstance(result["options"], list)
        self.assertGreater(len(result["options"]), 0)

    def test_long_reply_truncated(self):
        long_text = "word " * 500
        result = validate_story_response(
            {"reply": long_text, "options": ["ok"], "ended": False},
        )
        self.assertLessEqual(len(result["reply"]), 1010)  # ~1000 + "..."

    # --- T-02: list-type reply tests ---

    def test_list_reply_non_empty_preserved(self):
        """Non-empty list replies pass through unchanged."""
        reply_list = [
            {"character": "Марко", "text": "Кой е?"},
            {"character": "Разказвач", "text": "Мракът се сгъсти."},
        ]
        result = validate_story_response(
            {"reply": reply_list, "options": ["a"], "ended": False},
        )
        self.assertIsInstance(result["reply"], list)
        self.assertEqual(len(result["reply"]), 2)

    def test_list_reply_empty_gets_fallback(self):
        """Empty list replies get a fallback system message."""
        result = validate_story_response(
            {"reply": [], "options": ["a"], "ended": False},
        )
        self.assertIsInstance(result["reply"], list)
        self.assertEqual(len(result["reply"]), 1)
        self.assertEqual(result["reply"][0]["character"], "System")


class TestValidateStoryResponseNewValidations(unittest.TestCase):
    # --- location drift ---

    def test_location_drift_reverts_to_chapter_setting(self):
        """AI location shares no words with chapter.setting — revert."""
        chapter = _make_chapter("Оборът на Бай Марко")
        result = validate_story_response(
            {"reply": "ok", "options": ["a"], "ended": False, "location": "Цариград"},
            chapter=chapter,
        )
        self.assertEqual(result["location"], "Оборът на Бай Марко")

    def test_location_plausible_kept(self):
        """AI location shares a word with chapter.setting — keep it."""
        chapter = _make_chapter("Оборът на Бай Марко")
        result = validate_story_response(
            {"reply": "ok", "options": ["a"], "ended": False, "location": "пред обора"},
            chapter=chapter,
        )
        self.assertEqual(result["location"], "пред обора")

    def test_location_no_chapter_not_touched(self):
        """Without a chapter, location passes through unchanged."""
        result = validate_story_response(
            {"reply": "ok", "options": ["a"], "ended": False, "location": "Цариград"},
        )
        self.assertEqual(result["location"], "Цариград")

    # --- key_event ---

    def test_key_event_truncated_at_120_chars(self):
        long_event = "x" * 200
        result = validate_story_response(
            {"reply": "ok", "options": ["a"], "ended": False, "key_event": long_event},
        )
        self.assertEqual(len(result["key_event"]), 120)

    def test_key_event_removed_when_duplicate(self):
        state = _make_state(key_events=["hero revealed"])
        result = validate_story_response(
            {"reply": "ok", "options": ["a"], "ended": False, "key_event": "hero revealed"},
            state=state,
        )
        self.assertNotIn("key_event", result)

    def test_key_event_kept_when_new(self):
        state = _make_state(key_events=["something else"])
        result = validate_story_response(
            {"reply": "ok", "options": ["a"], "ended": False, "key_event": "hero revealed"},
            state=state,
        )
        self.assertIn("key_event", result)
        self.assertEqual(result["key_event"], "hero revealed")

    # --- characters_present ---

    def test_characters_present_removed_when_not_a_list(self):
        result = validate_story_response(
            {"reply": "ok", "options": ["a"], "ended": False, "characters_present": "Марко"},
        )
        self.assertNotIn("characters_present", result)

    def test_characters_present_removed_when_list_of_non_strings(self):
        result = validate_story_response(
            {"reply": "ok", "options": ["a"], "ended": False, "characters_present": [1, 2]},
        )
        self.assertNotIn("characters_present", result)

    def test_characters_present_capped_at_8(self):
        names = [f"person_{i}" for i in range(12)]
        result = validate_story_response(
            {"reply": "ok", "options": ["a"], "ended": False, "characters_present": names},
        )
        self.assertEqual(len(result["characters_present"]), 8)

    # --- trust_level ---

    def test_trust_level_removed_when_not_integer(self):
        result = validate_story_response(
            {"reply": "ok", "options": ["a"], "ended": False, "trust_level": "high"},
        )
        self.assertNotIn("trust_level", result)

    def test_trust_level_removed_when_out_of_range_high(self):
        result = validate_story_response(
            {"reply": "ok", "options": ["a"], "ended": False, "trust_level": 10},
        )
        self.assertNotIn("trust_level", result)

    def test_trust_level_removed_when_out_of_range_low(self):
        result = validate_story_response(
            {"reply": "ok", "options": ["a"], "ended": False, "trust_level": -10},
        )
        self.assertNotIn("trust_level", result)

    def test_trust_level_kept_when_valid(self):
        result = validate_story_response(
            {"reply": "ok", "options": ["a"], "ended": False, "trust_level": -1},
        )
        self.assertEqual(result["trust_level"], -1)

    # --- active_props ---

    def test_active_props_removed_when_not_a_list(self):
        result = validate_story_response(
            {"reply": "ok", "options": ["a"], "ended": False, "active_props": "pistol"},
        )
        self.assertNotIn("active_props", result)

    def test_active_props_removed_when_list_of_non_strings(self):
        result = validate_story_response(
            {"reply": "ok", "options": ["a"], "ended": False, "active_props": [123, 456]},
        )
        self.assertNotIn("active_props", result)

    def test_active_props_entries_truncated_at_60_chars(self):
        long_prop = "p" * 100
        result = validate_story_response(
            {"reply": "ok", "options": ["a"], "ended": False, "active_props": [long_prop]},
        )
        self.assertEqual(len(result["active_props"][0]), 60)

    def test_active_props_capped_at_10(self):
        props = [f"prop_{i}" for i in range(15)]
        result = validate_story_response(
            {"reply": "ok", "options": ["a"], "ended": False, "active_props": props},
        )
        self.assertEqual(len(result["active_props"]), 10)


if __name__ == "__main__":
    unittest.main()
