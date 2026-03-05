"""Tests for response_parser module.

Covers parse_ai_json_response (including balanced-brace extraction)
and validate_story_response (including list-reply branch — T-02).
"""

import unittest

from literaplay.response_parser import parse_ai_json_response, validate_story_response


class TestResponseParser(unittest.TestCase):
    def test_parse_plain_json(self):
        parsed = parse_ai_json_response('{"reply":"hi","options":["a","b","c"]}')
        self.assertEqual(parsed["reply"], "hi")

    def test_parse_markdown_fenced_json(self):
        text = """```json
{"reply":"hello","options":["1","2","3"]}
```"""
        parsed = parse_ai_json_response(text)
        self.assertEqual(parsed["reply"], "hello")

    def test_parse_embedded_json(self):
        text = 'Model answer: {"reply":"ok","options":[]} End.'
        parsed = parse_ai_json_response(text)
        self.assertEqual(parsed["reply"], "ok")

    def test_parse_invalid_returns_none(self):
        self.assertIsNone(parse_ai_json_response("not json"))

    def test_parse_empty_returns_none(self):
        self.assertIsNone(parse_ai_json_response(""))
        self.assertIsNone(parse_ai_json_response(None))

    def test_parse_nested_json(self):
        """Balanced-brace extraction handles nested objects."""
        text = 'prefix {"reply":"ok","meta":{"a":1}} suffix'
        parsed = parse_ai_json_response(text)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["reply"], "ok")
        self.assertEqual(parsed["meta"]["a"], 1)

    def test_parse_multiple_json_objects_returns_first(self):
        """When two JSON objects appear, the first balanced one is returned."""
        text = '{"reply":"first"} junk {"reply":"second"}'
        parsed = parse_ai_json_response(text)
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


if __name__ == "__main__":
    unittest.main()
