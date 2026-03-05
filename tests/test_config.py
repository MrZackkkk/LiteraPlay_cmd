"""Tests for config.save_api_key and save_model_name."""

import os
import tempfile
import unittest
from pathlib import Path


class TestSaveApiKey(unittest.TestCase):
    """Unit tests for config.save_api_key."""

    def setUp(self):
        # Snapshot module-level globals and env vars to restore after each test
        from literaplay import config

        self._orig_api_key = config.API_KEY
        self._orig_model = config.DEFAULT_MODEL
        self._orig_env_key = os.environ.get("GOOGLE_API_KEY")
        self._orig_env_model = os.environ.get("LITERAPLAY_MODEL")

    def tearDown(self):
        from literaplay import config

        config.API_KEY = self._orig_api_key
        config.DEFAULT_MODEL = self._orig_model
        # Restore or remove environment variables
        if self._orig_env_key is not None:
            os.environ["GOOGLE_API_KEY"] = self._orig_env_key
        else:
            os.environ.pop("GOOGLE_API_KEY", None)
        if self._orig_env_model is not None:
            os.environ["LITERAPLAY_MODEL"] = self._orig_env_model
        else:
            os.environ.pop("LITERAPLAY_MODEL", None)

    def test_save_api_key_writes_to_env_file(self):
        from literaplay.config import save_api_key

        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            tmp_path = f.name
        try:
            save_api_key("test-key-123", dotenv_path=tmp_path)

            content = Path(tmp_path).read_text(encoding="utf-8")
            self.assertIn("GOOGLE_API_KEY", content)
            self.assertIn("test-key-123", content)

            from literaplay import config

            self.assertEqual(config.API_KEY, "test-key-123")
            self.assertEqual(os.environ.get("GOOGLE_API_KEY"), "test-key-123")
        finally:
            os.unlink(tmp_path)

    def test_save_api_key_strips_whitespace(self):
        from literaplay.config import save_api_key

        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            tmp_path = f.name
        try:
            save_api_key("  spaced-key  ", dotenv_path=tmp_path)

            content = Path(tmp_path).read_text(encoding="utf-8")
            self.assertIn("spaced-key", content)
            self.assertNotIn("  spaced-key", content)
        finally:
            os.unlink(tmp_path)

    def test_save_api_key_rejects_empty(self):
        from literaplay.config import save_api_key

        with self.assertRaises(ValueError):
            save_api_key("")

    def test_save_api_key_rejects_whitespace_only(self):
        from literaplay.config import save_api_key

        with self.assertRaises(ValueError):
            save_api_key("   ")

    def test_save_model_name_writes_to_env_file(self):
        from literaplay.config import save_model_name

        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            tmp_path = f.name
        try:
            save_model_name("gemini-2.5-flash", dotenv_path=tmp_path)

            content = Path(tmp_path).read_text(encoding="utf-8")
            self.assertIn("LITERAPLAY_MODEL", content)
            self.assertIn("gemini-2.5-flash", content)

            from literaplay import config

            self.assertEqual(config.DEFAULT_MODEL, "gemini-2.5-flash")
            self.assertEqual(os.environ.get("LITERAPLAY_MODEL"), "gemini-2.5-flash")
        finally:
            os.unlink(tmp_path)

    def test_save_model_name_rejects_empty(self):
        from literaplay.config import save_model_name

        with self.assertRaises(ValueError):
            save_model_name("")


if __name__ == "__main__":
    unittest.main()
