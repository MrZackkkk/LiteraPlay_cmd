import unittest
from unittest.mock import MagicMock, patch

from ai_service import AIService


class TestAIService(unittest.TestCase):
    def setUp(self):
        self.api_key = "fake_key"
        self.model_name = "fake_model"

    @patch("ai_service.genai.Client")
    def test_init(self, mock_client_cls):
        service = AIService(self.api_key, self.model_name)
        self.assertIsNotNone(service.client)
        mock_client_cls.assert_called_with(api_key=self.api_key)

    @patch("ai_service.types.GenerateContentConfig")
    @patch("ai_service.genai.Client")
    def test_create_chat(self, mock_client_cls, mock_config_cls):
        service = AIService(self.api_key, self.model_name)
        mock_client_instance = mock_client_cls.return_value
        mock_chats = mock_client_instance.chats
        mock_chat_session = MagicMock()
        mock_chats.create.return_value = mock_chat_session

        mock_config_instance = mock_config_cls.return_value

        chat = service.create_chat("System Prompt")
        self.assertEqual(chat, mock_chat_session)

        # Verify GenerateContentConfig was called with correct parameters
        mock_config_cls.assert_called_once()
        _, kwargs = mock_config_cls.call_args
        self.assertEqual(kwargs['temperature'], 0.2)
        self.assertEqual(kwargs['top_p'], 0.95)
        self.assertEqual(kwargs['top_k'], 40)
        self.assertIn("System Prompt", kwargs['system_instruction'])
        self.assertIn("STRICT GUIDELINES", kwargs['system_instruction'])

        # Verify chats.create was called with the config
        mock_chats.create.assert_called_once_with(
            model=self.model_name,
            config=mock_config_instance,
            history=[],
        )

    @patch.object(AIService, "_init_client", return_value=None)
    def test_send_message_success(self, _mock_init):
        service = AIService(self.api_key, self.model_name)

        mock_chat_session = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "AI Response"
        mock_chat_session.send_message.return_value = mock_response

        response = service.send_message(mock_chat_session, "Hello")
        self.assertEqual(response, "AI Response")

    @patch.object(AIService, "_init_client", return_value=None)
    def test_send_message_retry(self, _mock_init):
        service = AIService(self.api_key, self.model_name)
        mock_chat_session = MagicMock()

        error_429 = Exception("429 Resource Exhausted")
        mock_response = MagicMock()
        mock_response.text = "Success after retry"
        mock_chat_session.send_message.side_effect = [error_429, mock_response]

        callback = MagicMock()

        with patch("time.sleep"):
            response = service.send_message(mock_chat_session, "Hello", status_callback=callback)

        self.assertEqual(response, "Success after retry")
        callback.assert_called_once()
        self.assertEqual(mock_chat_session.send_message.call_count, 2)

    @patch.object(AIService, "_init_client", return_value=None)
    def test_send_message_missing_text_returns_empty_string(self, _mock_init):
        service = AIService(self.api_key, self.model_name)
        mock_chat_session = MagicMock()
        mock_chat_session.send_message.return_value = object()

        response = service.send_message(mock_chat_session, "Hello")
        self.assertEqual(response, "")


if __name__ == "__main__":
    import logging

    logging.disable(logging.CRITICAL)
    unittest.main()
