import unittest
from unittest.mock import patch, MagicMock
from literaplay.main import validate_api_key

class TestMainLogic(unittest.TestCase):
    @patch("literaplay.main.validate_api_key_with_available_sdk")
    def test_validate_api_key_delegates(self, mock_validate):
        mock_validate.return_value = (True, "OK")
        res = validate_api_key("test_key")
        self.assertEqual(res, (True, "OK"))
        mock_validate.assert_called_once_with("test_key")

if __name__ == "__main__":
    unittest.main()
