import unittest
from unittest.mock import patch, MagicMock

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

if __name__ == "__main__":
    unittest.main()
