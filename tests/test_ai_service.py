"""Tests for ai_service module."""

import unittest
from unittest.mock import MagicMock, patch


class TestAIService(unittest.TestCase):
    def setUp(self):
        self.api_key = "fake_key"
        self.model_name = "fake_model"
        self.provider = "gemini"

    @patch("google.genai.Client")
    def test_init(self, mock_client_cls):
        from literaplay.ai_service import AIService

        service = AIService(self.provider, self.api_key, self.model_name)
        self.assertIsNotNone(service.client)
        mock_client_cls.assert_called_with(api_key=self.api_key)

    @patch("google.genai.Client")
    def test_create_chat(self, mock_client_cls):
        from literaplay.ai_service import AIService

        service = AIService(self.provider, self.api_key, self.model_name)
        mock_client_instance = mock_client_cls.return_value
        mock_chats = mock_client_instance.chats
        mock_chat_session = MagicMock()
        mock_chats.create.return_value = mock_chat_session

        chat = service.create_chat("System Prompt")

        # Verify chats.create was called with the model
        mock_chats.create.assert_called_once()
        _, kwargs = mock_chats.create.call_args
        self.assertEqual(kwargs["model"], self.model_name)

        self.assertIsNotNone(chat)

    @patch("google.genai.Client")
    def test_send_message_success(self, mock_client_cls):
        from literaplay.ai_service import AIService, ChatSession

        service = AIService(self.provider, self.api_key, self.model_name)

        # Create a mock ChatSession
        mock_gemini_chat = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "AI Response"
        mock_gemini_chat.send_message.return_value = mock_response

        chat_session = ChatSession("gemini", service.client, self.model_name, "system prompt")
        chat_session._gemini_chat = mock_gemini_chat

        response = service.send_message(chat_session, "Hello")
        self.assertEqual(response, "AI Response")

    @patch("literaplay.ai_service._interruptible_sleep")
    @patch("google.genai.Client")
    def test_send_message_retry(self, mock_client_cls, mock_sleep):
        from literaplay.ai_service import AIService, ChatSession

        service = AIService(self.provider, self.api_key, self.model_name)

        mock_gemini_chat = MagicMock()
        error_429 = Exception("429 Resource Exhausted")
        mock_response = MagicMock()
        mock_response.text = "Success after retry"
        mock_gemini_chat.send_message.side_effect = [error_429, mock_response]

        chat_session = ChatSession("gemini", service.client, self.model_name, "system prompt")
        chat_session._gemini_chat = mock_gemini_chat

        callback = MagicMock()
        response = service.send_message(chat_session, "Hello", status_callback=callback)

        self.assertEqual(response, "Success after retry")
        callback.assert_called_once()
        self.assertEqual(mock_gemini_chat.send_message.call_count, 2)
        self.assertTrue(mock_sleep.call_count > 0)

    @patch("google.genai.Client")
    def test_send_message_missing_text_returns_empty_string(self, mock_client_cls):
        from literaplay.ai_service import AIService, ChatSession

        service = AIService(self.provider, self.api_key, self.model_name)

        mock_gemini_chat = MagicMock()
        mock_gemini_chat.send_message.return_value = object()

        chat_session = ChatSession("gemini", service.client, self.model_name, "system prompt")
        chat_session._gemini_chat = mock_gemini_chat

        response = service.send_message(chat_session, "Hello")
        self.assertEqual(response, "")

    @patch("google.genai.Client")
    def test_send_message_with_context_prepends_context(self, mock_client_cls):
        from literaplay.ai_service import AIService, ChatSession

        service = AIService(self.provider, self.api_key, self.model_name)

        mock_gemini_chat = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Response"
        mock_gemini_chat.send_message.return_value = mock_response

        chat_session = ChatSession("gemini", service.client, self.model_name, "system prompt")
        chat_session._gemini_chat = mock_gemini_chat

        service.send_message_with_context(chat_session, "Hello", "Chapter: Test")

        sent_text = mock_gemini_chat.send_message.call_args[0][0]
        self.assertIn("[CONTEXT]", sent_text)
        self.assertIn("Chapter: Test", sent_text)
        self.assertIn("User: Hello", sent_text)

    @patch("google.genai.Client")
    def test_send_message_with_context_empty_context(self, mock_client_cls):
        from literaplay.ai_service import AIService, ChatSession

        service = AIService(self.provider, self.api_key, self.model_name)

        mock_gemini_chat = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Response"
        mock_gemini_chat.send_message.return_value = mock_response

        chat_session = ChatSession("gemini", service.client, self.model_name, "system prompt")
        chat_session._gemini_chat = mock_gemini_chat

        service.send_message_with_context(chat_session, "Hello", "")

        sent_text = mock_gemini_chat.send_message.call_args[0][0]
        self.assertEqual(sent_text, "Hello")
        self.assertNotIn("[CONTEXT]", sent_text)

    @patch("literaplay.ai_service._interruptible_sleep")
    @patch("google.genai.Client")
    def test_send_message_raises_overload_after_max_retries(self, mock_client_cls, mock_sleep):
        from literaplay.ai_service import AIService, APIOverloadedError, ChatSession

        service = AIService(self.provider, self.api_key, self.model_name)

        mock_gemini_chat = MagicMock()
        mock_gemini_chat.send_message.side_effect = Exception("429 Resource Exhausted")

        chat_session = ChatSession("gemini", service.client, self.model_name, "system prompt")
        chat_session._gemini_chat = mock_gemini_chat

        with self.assertRaises(APIOverloadedError):
            service.send_message(chat_session, "Hello")

        self.assertEqual(mock_gemini_chat.send_message.call_count, 3)

    @patch("google.genai.Client")
    def test_send_message_non_overload_error_raises_immediately(self, mock_client_cls):
        from literaplay.ai_service import AIService, ChatSession

        service = AIService(self.provider, self.api_key, self.model_name)

        mock_gemini_chat = MagicMock()
        mock_gemini_chat.send_message.side_effect = ValueError("Something else broke")

        chat_session = ChatSession("gemini", service.client, self.model_name, "system prompt")
        chat_session._gemini_chat = mock_gemini_chat

        with self.assertRaises(ValueError):
            service.send_message(chat_session, "Hello")

        self.assertEqual(mock_gemini_chat.send_message.call_count, 1)

    @patch("literaplay.ai_service._interruptible_sleep")
    @patch("google.genai.Client")
    def test_send_message_retry_callback_has_bulgarian_text(self, mock_client_cls, mock_sleep):
        from literaplay.ai_service import AIService, ChatSession

        service = AIService(self.provider, self.api_key, self.model_name)

        mock_gemini_chat = MagicMock()
        error_429 = Exception("429 Resource Exhausted")
        mock_response = MagicMock()
        mock_response.text = "OK"
        mock_gemini_chat.send_message.side_effect = [error_429, mock_response]

        chat_session = ChatSession("gemini", service.client, self.model_name, "system prompt")
        chat_session._gemini_chat = mock_gemini_chat

        callback = MagicMock()
        service.send_message(chat_session, "Hello", status_callback=callback)

        callback.assert_called_once()
        msg = callback.call_args[0][0]
        self.assertIn("Претоварен", msg)
        self.assertIn("1/3", msg)

    def test_init_requires_provider(self):
        from literaplay.ai_service import AIService

        with self.assertRaises(ValueError):
            AIService("", self.api_key, self.model_name)

    def test_init_requires_api_key(self):
        from literaplay.ai_service import AIService

        with self.assertRaises(ValueError):
            AIService(self.provider, "", self.model_name)


class TestSanitizeApiError(unittest.TestCase):
    """T-03: Tests for the security-critical _sanitize_api_error function."""

    def test_strips_literal_key(self):
        from literaplay.ai_service import _sanitize_api_error

        key = "AIzaSyFakeKey12345"
        exc = Exception(f"Error at https://api.example.com/v1?key={key}&foo=bar")
        result = _sanitize_api_error(exc, key)
        self.assertNotIn(key, result)
        self.assertIn("***", result)

    def test_strips_key_query_param(self):
        from literaplay.ai_service import _sanitize_api_error

        exc = Exception("Error at https://api.example.com/v1?key=SomeOtherKey123")
        result = _sanitize_api_error(exc, "not-the-key")
        self.assertNotIn("SomeOtherKey123", result)
        self.assertIn("?key=***", result)

    def test_strips_ampersand_key_param(self):
        from literaplay.ai_service import _sanitize_api_error

        exc = Exception("Error at https://api.example.com/v1?foo=bar&key=Secret456")
        result = _sanitize_api_error(exc, "not-the-key")
        self.assertNotIn("Secret456", result)

    def test_empty_key_does_not_crash(self):
        from literaplay.ai_service import _sanitize_api_error

        exc = Exception("Some error")
        result = _sanitize_api_error(exc, "")
        self.assertEqual(result, "Some error")

    def test_none_key_does_not_crash(self):
        from literaplay.ai_service import _sanitize_api_error

        exc = Exception("Some error")
        result = _sanitize_api_error(exc, None)
        self.assertEqual(result, "Some error")

    def test_preserves_useful_message(self):
        from literaplay.ai_service import _sanitize_api_error

        exc = Exception("Model not found: gemini-pro")
        result = _sanitize_api_error(exc, "test-key")
        self.assertIn("Model not found: gemini-pro", result)


class TestValidateApiKey(unittest.TestCase):
    @patch("literaplay.config.PROVIDER_MODELS", {"gemini": {"default": "gemini-test", "models": []}})
    @patch("google.genai.Client")
    def test_validate_api_key_uses_generate_content(self, mock_client_cls):
        from literaplay.ai_service import validate_api_key

        mock_client = mock_client_cls.return_value
        ok, message = validate_api_key("gemini", "valid-key")

        self.assertTrue(ok)
        self.assertIn("валиден", message)
        mock_client.models.generate_content.assert_called_once()

    @patch("literaplay.config.PROVIDER_MODELS", {"gemini": {"default": "gemini-test", "models": []}})
    @patch("google.genai.Client")
    def test_validate_api_key_falls_back_to_list_models(self, mock_client_cls):
        from literaplay.ai_service import validate_api_key

        mock_client = mock_client_cls.return_value
        mock_client.models.generate_content.side_effect = Exception("generation blocked")
        mock_client.models.list.return_value = iter([object()])

        ok, message = validate_api_key("gemini", "valid-key")

        self.assertTrue(ok)
        self.assertIn("валиден", message)
        mock_client.models.list.assert_called_once()

    def test_validate_api_key_empty_key(self):
        from literaplay.ai_service import validate_api_key

        ok, message = validate_api_key("gemini", "")
        self.assertFalse(ok)

    def test_validate_api_key_unknown_provider(self):
        from literaplay.ai_service import validate_api_key

        ok, message = validate_api_key("unknown_provider", "some-key")
        self.assertFalse(ok)
        self.assertIn("Непознат", message)


class TestChatSession(unittest.TestCase):
    def test_openai_send_message(self):
        from literaplay.ai_service import ChatSession

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Hello back"
        mock_client.chat.completions.create.return_value = mock_response

        session = ChatSession("openai", mock_client, "gpt-4.1-mini", "system prompt")
        result = session.send_message("Hello")

        self.assertEqual(result, "Hello back")
        self.assertEqual(len(session.history), 2)
        self.assertEqual(session.history[0]["role"], "user")
        self.assertEqual(session.history[1]["role"], "assistant")

    def test_anthropic_send_message(self):
        from literaplay.ai_service import ChatSession

        mock_client = MagicMock()
        mock_content = MagicMock()
        mock_content.text = "Bonjour"
        mock_response = MagicMock()
        mock_response.content = [mock_content]
        mock_client.messages.create.return_value = mock_response

        session = ChatSession("anthropic", mock_client, "claude-sonnet-4-6", "system prompt")
        result = session.send_message("Hi")

        self.assertEqual(result, "Bonjour")
        self.assertEqual(len(session.history), 2)

    def test_unknown_provider_raises(self):
        from literaplay.ai_service import ChatSession

        session = ChatSession("unknown", None, "model", "prompt")
        with self.assertRaises(ValueError):
            session.send_message("hello")


if __name__ == "__main__":
    import logging

    logging.disable(logging.CRITICAL)
    unittest.main()
