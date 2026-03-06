"""Tests for ai_service module."""

import unittest
from unittest.mock import MagicMock, patch

from literaplay.ai_service import AIService, APIOverloadedError, _sanitize_api_error


class TestAIService(unittest.TestCase):
    def setUp(self):
        self.api_key = "fake_key"
        self.model_name = "fake_model"

    @patch("literaplay.ai_service.genai.Client")
    def test_init(self, mock_client_cls):
        service = AIService(self.api_key, self.model_name)
        self.assertIsNotNone(service.client)
        mock_client_cls.assert_called_with(api_key=self.api_key)

    @patch("literaplay.ai_service.types.GenerateContentConfig")
    @patch("literaplay.ai_service.genai.Client")
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
        self.assertEqual(kwargs["temperature"], 0.2)
        self.assertEqual(kwargs["top_p"], 0.95)
        self.assertEqual(kwargs["top_k"], 40)
        self.assertIn("System Prompt", kwargs["system_instruction"])
        self.assertIn("STRICT GUIDELINES", kwargs["system_instruction"])

        # Verify chats.create was called with the config
        mock_chats.create.assert_called_once_with(
            model=self.model_name,
            config=mock_config_instance,
            history=[],
        )

    @patch("literaplay.ai_service.genai.Client")
    def test_send_message_success(self, mock_client_cls):
        service = AIService(self.api_key, self.model_name)

        mock_chat_session = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "AI Response"
        mock_chat_session.send_message.return_value = mock_response

        response = service.send_message(mock_chat_session, "Hello")
        self.assertEqual(response, "AI Response")

    @patch("literaplay.ai_service._interruptible_sleep")
    @patch("literaplay.ai_service.genai.Client")
    def test_send_message_retry(self, mock_client_cls, mock_sleep):
        service = AIService(self.api_key, self.model_name)
        mock_chat_session = MagicMock()

        error_429 = Exception("429 Resource Exhausted")
        mock_response = MagicMock()
        mock_response.text = "Success after retry"
        mock_chat_session.send_message.side_effect = [error_429, mock_response]

        callback = MagicMock()

        response = service.send_message(mock_chat_session, "Hello", status_callback=callback)

        self.assertEqual(response, "Success after retry")
        callback.assert_called_once()
        self.assertEqual(mock_chat_session.send_message.call_count, 2)
        # Verify sleep was called (interruptible chunks)
        self.assertTrue(mock_sleep.call_count > 0)

    @patch("literaplay.ai_service.genai.Client")
    def test_send_message_missing_text_returns_empty_string(self, mock_client_cls):
        service = AIService(self.api_key, self.model_name)
        mock_chat_session = MagicMock()
        mock_chat_session.send_message.return_value = object()

        response = service.send_message(mock_chat_session, "Hello")
        self.assertEqual(response, "")

    @patch("literaplay.ai_service.genai.Client")
    def test_send_message_with_context_prepends_context(self, mock_client_cls):
        service = AIService(self.api_key, self.model_name)
        mock_chat_session = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Response"
        mock_chat_session.send_message.return_value = mock_response

        service.send_message_with_context(mock_chat_session, "Hello", "Chapter: Test")

        sent_text = mock_chat_session.send_message.call_args[0][0]
        self.assertIn("[CONTEXT]", sent_text)
        self.assertIn("Chapter: Test", sent_text)
        self.assertIn("User: Hello", sent_text)

    @patch("literaplay.ai_service.genai.Client")
    def test_send_message_with_context_empty_context(self, mock_client_cls):
        service = AIService(self.api_key, self.model_name)
        mock_chat_session = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Response"
        mock_chat_session.send_message.return_value = mock_response

        service.send_message_with_context(mock_chat_session, "Hello", "")

        sent_text = mock_chat_session.send_message.call_args[0][0]
        self.assertEqual(sent_text, "Hello")
        self.assertNotIn("[CONTEXT]", sent_text)


    @patch("literaplay.ai_service._interruptible_sleep")
    @patch("literaplay.ai_service.genai.Client")
    def test_send_message_raises_overload_after_max_retries(self, mock_client_cls, mock_sleep):
        service = AIService(self.api_key, self.model_name)
        mock_chat_session = MagicMock()
        mock_chat_session.send_message.side_effect = Exception("429 Resource Exhausted")

        with self.assertRaises(APIOverloadedError):
            service.send_message(mock_chat_session, "Hello")

        self.assertEqual(mock_chat_session.send_message.call_count, 3)

    @patch("literaplay.ai_service.genai.Client")
    def test_send_message_non_overload_error_raises_immediately(self, mock_client_cls):
        service = AIService(self.api_key, self.model_name)
        mock_chat_session = MagicMock()
        mock_chat_session.send_message.side_effect = ValueError("Something else broke")

        with self.assertRaises(ValueError):
            service.send_message(mock_chat_session, "Hello")

        self.assertEqual(mock_chat_session.send_message.call_count, 1)

    @patch("literaplay.ai_service._interruptible_sleep")
    @patch("literaplay.ai_service.genai.Client")
    def test_send_message_retry_callback_has_bulgarian_text(self, mock_client_cls, mock_sleep):
        service = AIService(self.api_key, self.model_name)
        mock_chat_session = MagicMock()

        error_429 = Exception("429 Resource Exhausted")
        mock_response = MagicMock()
        mock_response.text = "OK"
        mock_chat_session.send_message.side_effect = [error_429, mock_response]

        callback = MagicMock()
        service.send_message(mock_chat_session, "Hello", status_callback=callback)

        callback.assert_called_once()
        msg = callback.call_args[0][0]
        self.assertIn("Претоварен", msg)
        self.assertIn("1/3", msg)


class TestSanitizeApiError(unittest.TestCase):
    """T-03: Tests for the security-critical _sanitize_api_error function."""

    def test_strips_literal_key(self):
        key = "AIzaSyFakeKey12345"
        exc = Exception(f"Error at https://api.example.com/v1?key={key}&foo=bar")
        result = _sanitize_api_error(exc, key)
        self.assertNotIn(key, result)
        self.assertIn("***", result)

    def test_strips_key_query_param(self):
        exc = Exception("Error at https://api.example.com/v1?key=SomeOtherKey123")
        result = _sanitize_api_error(exc, "not-the-key")
        self.assertNotIn("SomeOtherKey123", result)
        self.assertIn("?key=***", result)

    def test_strips_ampersand_key_param(self):
        exc = Exception("Error at https://api.example.com/v1?foo=bar&key=Secret456")
        result = _sanitize_api_error(exc, "not-the-key")
        self.assertNotIn("Secret456", result)

    def test_empty_key_does_not_crash(self):
        exc = Exception("Some error")
        result = _sanitize_api_error(exc, "")
        self.assertEqual(result, "Some error")

    def test_none_key_does_not_crash(self):
        exc = Exception("Some error")
        result = _sanitize_api_error(exc, None)
        self.assertEqual(result, "Some error")

    def test_preserves_useful_message(self):
        exc = Exception("Model not found: gemini-pro")
        result = _sanitize_api_error(exc, "test-key")
        self.assertIn("Model not found: gemini-pro", result)


class TestValidateApiKey(unittest.TestCase):
    @patch("literaplay.config.DEFAULT_MODEL", "gemini-test")
    @patch("literaplay.ai_service.genai.Client")
    def test_validate_api_key_uses_generate_content(self, mock_client_cls):
        from literaplay.ai_service import validate_api_key_with_available_sdk

        mock_client = mock_client_cls.return_value
        ok, message = validate_api_key_with_available_sdk("valid-key")

        self.assertTrue(ok)
        self.assertIn("валиден", message)
        mock_client.models.generate_content.assert_called_once()

    @patch("literaplay.config.DEFAULT_MODEL", "gemini-test")
    @patch("literaplay.ai_service.genai.Client")
    def test_validate_api_key_falls_back_to_list_models(self, mock_client_cls):
        from literaplay.ai_service import validate_api_key_with_available_sdk

        mock_client = mock_client_cls.return_value
        mock_client.models.generate_content.side_effect = Exception("generation blocked")
        mock_client.models.list.return_value = iter([object()])

        ok, message = validate_api_key_with_available_sdk("valid-key")

        self.assertTrue(ok)
        self.assertIn("валиден", message)
        mock_client.models.list.assert_called_once()


if __name__ == "__main__":
    import logging

    logging.disable(logging.CRITICAL)
    unittest.main()
