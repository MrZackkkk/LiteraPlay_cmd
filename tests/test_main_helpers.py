"""Tests for main.py helper functions and BackendBridge logic."""

import unittest

from literaplay.main import _format_reply_messages


class TestFormatReplyMessages(unittest.TestCase):
    """Unit tests for the _format_reply_messages helper."""

    def test_plain_string_reply(self):
        result = _format_reply_messages("Hello world", "Марко")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["sender"], "Марко")
        self.assertEqual(result[0]["text"], "Hello world")
        self.assertFalse(result[0]["isUser"])
        self.assertFalse(result[0]["isSystem"])

    def test_list_reply(self):
        reply = [
            {"character": "Бай Марко", "text": "Кой е?"},
            {"character": "Разказвач", "text": "Мракът се сгъсти."},
        ]
        result = _format_reply_messages(reply, "default")
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["sender"], "Бай Марко")
        self.assertEqual(result[0]["text"], "Кой е?")
        self.assertEqual(result[1]["sender"], "Разказвач")

    def test_list_reply_missing_character_uses_default(self):
        reply = [{"text": "Some text"}]
        result = _format_reply_messages(reply, "Fallback")
        self.assertEqual(result[0]["sender"], "Fallback")

    def test_list_reply_missing_text_gives_empty_string(self):
        reply = [{"character": "Hero"}]
        result = _format_reply_messages(reply, "default")
        self.assertEqual(result[0]["text"], "")

    def test_empty_list_reply(self):
        result = _format_reply_messages([], "default")
        self.assertEqual(result, [])

    def test_non_string_reply_coerced(self):
        result = _format_reply_messages(42, "Bot")
        self.assertEqual(result[0]["text"], "42")

    def test_all_messages_marked_not_user_not_system(self):
        reply = [{"character": "A", "text": "hi"}, {"character": "B", "text": "bye"}]
        result = _format_reply_messages(reply, "default")
        for msg in result:
            self.assertFalse(msg["isUser"])
            self.assertFalse(msg["isSystem"])


if __name__ == "__main__":
    unittest.main()
