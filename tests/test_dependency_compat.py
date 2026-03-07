import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import literaplay.dependency_compat as compat


class TestDependencyCompat(unittest.TestCase):
    @patch("literaplay.dependency_compat.import_module")
    def test_load_dotenv_success(self, mock_import):
        mock_module = MagicMock()
        mock_module.load_dotenv = "fake_load"
        mock_module.set_key = "fake_set"
        mock_import.return_value = mock_module

        load_fn, set_fn = compat.load_dotenv_functions()
        self.assertEqual(load_fn, "fake_load")
        self.assertEqual(set_fn, "fake_set")

    @patch("literaplay.dependency_compat.import_module")
    def test_load_dotenv_fallback(self, mock_import):
        mock_import.side_effect = ModuleNotFoundError("No python-dotenv")

        load_fn, set_fn = compat.load_dotenv_functions()
        # Fallback functions should be callable without error
        load_fn()
        set_fn(".env", "KEY", "VALUE")
        # Ensure we didn't crash
        self.assertTrue(True)


class TestFallbackLoadDotenv(unittest.TestCase):
    """Test _fallback_load_dotenv with real temp files."""

    def test_loads_simple_key_value(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("TEST_COMPAT_KEY=hello\n")
            f.flush()
            env_key = "TEST_COMPAT_KEY"
            # Clear env first
            os.environ.pop(env_key, None)
            result = compat._fallback_load_dotenv(f.name)
            self.assertTrue(result)
            self.assertEqual(os.environ.get(env_key), "hello")
            os.environ.pop(env_key, None)
            os.unlink(f.name)

    def test_skips_comments_and_blank_lines(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("# This is a comment\n\nTEST_COMPAT_B=value\n")
            f.flush()
            os.environ.pop("TEST_COMPAT_B", None)
            compat._fallback_load_dotenv(f.name)
            self.assertEqual(os.environ.get("TEST_COMPAT_B"), "value")
            os.environ.pop("TEST_COMPAT_B", None)
            os.unlink(f.name)

    def test_strips_quotes(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write('TEST_COMPAT_C="quoted_value"\n')
            f.flush()
            os.environ.pop("TEST_COMPAT_C", None)
            compat._fallback_load_dotenv(f.name)
            self.assertEqual(os.environ.get("TEST_COMPAT_C"), "quoted_value")
            os.environ.pop("TEST_COMPAT_C", None)
            os.unlink(f.name)

    def test_nonexistent_file_returns_false(self):
        result = compat._fallback_load_dotenv("/tmp/nonexistent_env_file_12345")
        self.assertFalse(result)


class TestFallbackSetKey(unittest.TestCase):
    """Test _fallback_set_key with real temp files."""

    def test_creates_new_key(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("EXISTING=value\n")
            f.flush()
            compat._fallback_set_key(f.name, "NEW_KEY", "new_value")
            with open(f.name) as fh:
                content = fh.read()
            self.assertIn('NEW_KEY="new_value"', content)
            self.assertIn("EXISTING=value", content)
            os.unlink(f.name)

    def test_overwrites_existing_key(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("MY_KEY=old_value\n")
            f.flush()
            compat._fallback_set_key(f.name, "MY_KEY", "new_value")
            with open(f.name) as fh:
                content = fh.read()
            self.assertIn('MY_KEY="new_value"', content)
            self.assertNotIn("old_value", content)
            os.unlink(f.name)

    def test_returns_tuple(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("")
            f.flush()
            result = compat._fallback_set_key(f.name, "K", "V")
            self.assertEqual(result, (True, "K", "V"))
            os.unlink(f.name)


if __name__ == "__main__":
    unittest.main()
