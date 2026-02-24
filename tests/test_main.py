import unittest
from unittest.mock import patch, MagicMock


class TestBackendBridge(unittest.TestCase):
    """Verify that BackendBridge dispatches API key verification to a worker."""

    @patch("literaplay.main.AIService")
    @patch("literaplay.main.config")
    def test_verify_api_key_starts_worker(self, mock_config, mock_ai_cls):
        mock_config.API_KEY = None
        mock_config.DEFAULT_MODEL = "test-model"

        from literaplay.main import BackendBridge

        bridge = BackendBridge(app_window=MagicMock())

        with patch("literaplay.main.APIVerifyWorker") as mock_worker_cls:
            mock_worker = MagicMock()
            mock_worker_cls.return_value = mock_worker

            bridge.verify_api_key("test-key")

            mock_worker_cls.assert_called_once_with("test-key")
            mock_worker.start.assert_called_once()


if __name__ == "__main__":
    unittest.main()
