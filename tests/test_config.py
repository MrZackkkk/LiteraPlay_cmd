"""Tests for config.save_api_key."""

import os
import unittest
from pathlib import Path


class TestSaveApiKey(unittest.TestCase):
    """Unit tests for config.save_api_key."""

    def test_save_api_key_writes_to_env_file(self, ):
        from literaplay.config import save_api_key

        tmp_env = Path("test_env_tmp.env")
        try:
            save_api_key("test-key-123", dotenv_path=str(tmp_env))

            content = tmp_env.read_text(encoding="utf-8")
            self.assertIn("GOOGLE_API_KEY", content)
            self.assertIn("test-key-123", content)

            # Verify runtime globals were updated
            from literaplay import config

            self.assertEqual(config.API_KEY, "test-key-123")
            self.assertEqual(os.environ.get("GOOGLE_API_KEY"), "test-key-123")
        finally:
            if tmp_env.exists():
                tmp_env.unlink()
            # Reset environment
            os.environ.pop("GOOGLE_API_KEY", None)

    def test_save_api_key_strips_whitespace(self):
        from literaplay.config import save_api_key

        tmp_env = Path("test_env_tmp2.env")
        try:
            save_api_key("  spaced-key  ", dotenv_path=str(tmp_env))

            content = tmp_env.read_text(encoding="utf-8")
            self.assertIn("spaced-key", content)
            self.assertNotIn("  spaced-key", content)
        finally:
            if tmp_env.exists():
                tmp_env.unlink()
            os.environ.pop("GOOGLE_API_KEY", None)

    def test_save_api_key_rejects_empty(self):
        from literaplay.config import save_api_key

        with self.assertRaises(ValueError):
            save_api_key("")

    def test_save_api_key_rejects_whitespace_only(self):
        from literaplay.config import save_api_key

        with self.assertRaises(ValueError):
            save_api_key("   ")


if __name__ == "__main__":
    unittest.main()
