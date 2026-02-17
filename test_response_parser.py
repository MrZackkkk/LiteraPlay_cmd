import unittest

from response_parser import parse_ai_json_response


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


if __name__ == "__main__":
    unittest.main()
