"""Tests for config.save_api_key, save_model_name, and save_provider."""

import os
import tempfile
import unittest
from pathlib import Path


class TestSaveApiKey(unittest.TestCase):
    """Unit tests for config.save_api_key."""

    def setUp(self):
        from literaplay import config

        self._orig_api_key = config.API_KEY
        self._orig_model = config.DEFAULT_MODEL
        self._orig_provider = config.PROVIDER
        self._orig_env_key = os.environ.get("LITERAPLAY_API_KEY")
        self._orig_env_model = os.environ.get("LITERAPLAY_MODEL")
        self._orig_env_provider = os.environ.get("LITERAPLAY_PROVIDER")

    def tearDown(self):
        from literaplay import config

        config.API_KEY = self._orig_api_key
        config.DEFAULT_MODEL = self._orig_model
        config.PROVIDER = self._orig_provider
        for var, orig in [
            ("LITERAPLAY_API_KEY", self._orig_env_key),
            ("LITERAPLAY_MODEL", self._orig_env_model),
            ("LITERAPLAY_PROVIDER", self._orig_env_provider),
        ]:
            if orig is not None:
                os.environ[var] = orig
            else:
                os.environ.pop(var, None)

    def test_save_api_key_writes_to_env_file(self):
        from literaplay.config import save_api_key

        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            tmp_path = f.name
        try:
            save_api_key("test-key-123", dotenv_path=tmp_path)

            content = Path(tmp_path).read_text(encoding="utf-8")
            self.assertIn("LITERAPLAY_API_KEY", content)
            self.assertIn("test-key-123", content)

            from literaplay import config

            self.assertEqual(config.API_KEY, "test-key-123")
            self.assertEqual(os.environ.get("LITERAPLAY_API_KEY"), "test-key-123")
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

    def test_save_provider_writes_to_env_file(self):
        from literaplay.config import save_provider

        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            tmp_path = f.name
        try:
            save_provider("openai", dotenv_path=tmp_path)

            content = Path(tmp_path).read_text(encoding="utf-8")
            self.assertIn("LITERAPLAY_PROVIDER", content)
            self.assertIn("openai", content)

            from literaplay import config

            self.assertEqual(config.PROVIDER, "openai")
            self.assertEqual(os.environ.get("LITERAPLAY_PROVIDER"), "openai")
        finally:
            os.unlink(tmp_path)

    def test_save_provider_rejects_unknown(self):
        from literaplay.config import save_provider

        with self.assertRaises(ValueError):
            save_provider("unknown_provider")

    def test_get_default_model_for_provider(self):
        from literaplay.config import get_default_model_for_provider

        self.assertEqual(get_default_model_for_provider("gemini"), "gemini-2.5-flash")
        self.assertEqual(get_default_model_for_provider("openai"), "gpt-4.1-mini")
        self.assertEqual(get_default_model_for_provider("anthropic"), "claude-sonnet-4-6")
        self.assertEqual(get_default_model_for_provider("unknown"), "")

    def test_get_models_json(self):
        import json

        from literaplay.config import get_models_json

        result = json.loads(get_models_json("gemini"))
        self.assertIn("default", result)
        self.assertIn("models", result)
        self.assertTrue(len(result["models"]) > 0)

    def test_provider_models_structure(self):
        from literaplay.config import PROVIDER_MODELS

        for provider_name, provider_data in PROVIDER_MODELS.items():
            self.assertIn("default", provider_data, f"Missing 'default' for {provider_name}")
            self.assertIn("models", provider_data, f"Missing 'models' for {provider_name}")
            model_values = [m["value"] for m in provider_data["models"]]
            self.assertIn(
                provider_data["default"],
                model_values,
                f"Default model for {provider_name} not in model list",
            )


if __name__ == "__main__":
    unittest.main()
