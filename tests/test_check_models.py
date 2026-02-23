import unittest
from unittest.mock import patch, MagicMock
import io
import sys
from literaplay.check_models import main

class TestCheckModels(unittest.TestCase):
    @patch("literaplay.check_models.config.API_KEY", "fake_key")
    @patch("google.genai.Client")
    def test_check_models_script_success(self, mock_client_cls):
        mock_client = MagicMock()
        mock_model = MagicMock()
        mock_model.name = "models/gemini-pro"
        mock_client.models.list.return_value = [mock_model]
        mock_client_cls.return_value = mock_client
        
        captured_output = io.StringIO()
        sys.stdout = captured_output
        try:
            main()
        finally:
            sys.stdout = sys.__stdout__

        stdout_val = captured_output.getvalue()
        self.assertIn("gemini-pro", stdout_val)
        
    @patch("literaplay.check_models.config.API_KEY", "")
    def test_no_api_key(self):
        with patch("builtins.exit") as mock_exit:
            with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
                main()
                self.assertIn("not found in config", mock_stdout.getvalue())
                mock_exit.assert_called_once()
                
if __name__ == "__main__":
    unittest.main()
