import logging
import time
from typing import Callable, Optional

try:
    # Preferred import style for current google-genai SDK.
    import google.genai as genai
    from google.genai import types
except ImportError as exc:  # pragma: no cover - triggered only in broken environments
    genai = None
    types = None
    GENAI_IMPORT_ERROR = exc
else:
    GENAI_IMPORT_ERROR = None

try:
    import google.generativeai as legacy_genai
except ImportError as exc:  # pragma: no cover - triggered only when legacy SDK is absent
    legacy_genai = None
    LEGACY_GENAI_IMPORT_ERROR = exc
else:
    LEGACY_GENAI_IMPORT_ERROR = None


# Strict instruction to append to system prompts
STRICT_SYSTEM_INSTRUCTION = """
IMPORTANT STRICT GUIDELINES:
- **FACTUAL ACCURACY**: You must adhere strictly to the canonical facts of the literary universe. Do not invent key plot points or characters unless consistent with the setting.
- **CHARACTER CONSISTENCY**: Stay in character at all times. Use appropriate language and tone.
- **DYNAMIC SITUATION**: The situation evolves based on the conversation history. React to previous events and choices.
- **NO HALLUCINATIONS**: Do not reference modern technology or concepts unless relevant to the specific prompt.
"""


class _LegacyChatAdapter:
    """Adapter that exposes the same send_message().text shape used by the new SDK."""

    def __init__(self, chat_session):
        self._chat_session = chat_session

    def send_message(self, text: str):
        response = self._chat_session.send_message(text)
        if getattr(response, "text", None) is None:
            response.text = ""
        return response


def validate_api_key_with_available_sdk(key: str) -> tuple[bool, str]:
    """Validate API key through whichever Gemini SDK is available locally."""
    cleaned_key = (key or "").strip()
    if not cleaned_key:
        return False, "Моля, въведете API ключ."

    if genai is not None:
        try:
            client = genai.Client(api_key=cleaned_key)
            next(iter(client.models.list()), None)
            return True, "Ключът е валиден."
        except Exception as exc:
            return False, f"Невалиден ключ или проблем с API: {exc}"

    if legacy_genai is not None:
        try:
            legacy_genai.configure(api_key=cleaned_key)
            next(iter(legacy_genai.list_models()), None)
            return True, "Ключът е валиден."
        except Exception as exc:
            return False, f"Невалиден ключ или проблем с API: {exc}"

    return False, (
        "Не е намерен Gemini SDK. Инсталирай `pip install -U google-genai` "
        "(или като временен вариант `pip install -U google-generativeai`)."
    )


class AIService:
    def __init__(self, api_key: str, model_name: str):
        if not api_key:
            raise ValueError("API Key is required")

        self.api_key = api_key
        self.model_name = model_name
        self.client = None
        self._client_kind = ""
        self._init_client()

    def _init_client(self):
        if genai is None and legacy_genai is None:
            raise RuntimeError(
                "Gemini SDK is not available. Install/update it with "
                "`pip install -U google-genai` and remove conflicting `google` package "
                "if present."
            ) from (GENAI_IMPORT_ERROR or LEGACY_GENAI_IMPORT_ERROR)

        try:
            if genai is not None:
                self.client = genai.Client(api_key=self.api_key)
                self._client_kind = "modern"
                logging.info("GenAI Client initialized (google-genai).")
            else:
                legacy_genai.configure(api_key=self.api_key)
                self.client = legacy_genai
                self._client_kind = "legacy"
                logging.info("GenAI Client initialized (google-generativeai).")
        except Exception as e:
            logging.error(f"Failed to initialize GenAI client: {e}")
            raise

    def create_chat(self, system_instruction: str, response_mime_type: str = "application/json"):
        """Creates a new chat session with the given system instruction."""
        if not self.client:
            raise RuntimeError("Client not initialized")

        enhanced_instruction = f"{system_instruction}\n\n{STRICT_SYSTEM_INSTRUCTION}"

        try:
            if self._client_kind == "modern":
                config = types.GenerateContentConfig(
                    temperature=0.2,
                    top_p=0.95,
                    top_k=40,
                    system_instruction=enhanced_instruction,
                    response_mime_type=response_mime_type,
                )
                return self.client.chats.create(
                    model=self.model_name,
                    config=config,
                    history=[],
                )

            model = self.client.GenerativeModel(
                model_name=self.model_name,
                system_instruction=enhanced_instruction,
                generation_config={
                    "temperature": 0.2,
                    "top_p": 0.95,
                    "top_k": 40,
                    "response_mime_type": response_mime_type,
                },
            )
            return _LegacyChatAdapter(model.start_chat(history=[]))
        except Exception as e:
            logging.error(f"Failed to create chat: {e}")
            raise

    def send_message(self, chat_session, text: str, status_callback: Optional[Callable[[str], None]] = None) -> str:
        """
        Sends a message to the chat session and returns the response text.
        Handles rate limiting (429) with retries.
        """
        if not chat_session:
            raise ValueError("Chat session is not active")

        max_retries = 3
        retry_delay = 2

        for attempt in range(max_retries):
            try:
                response = chat_session.send_message(text)
                return getattr(response, "text", "") or ""
            except Exception as e:
                err_msg = str(e)
                # Check for 429 (Resource Exhausted)
                if "429" in err_msg and attempt < max_retries - 1:
                    msg = f"Overloaded. Retrying in {retry_delay}s... (Attempt {attempt + 1})"
                    logging.warning(msg)
                    if status_callback:
                        status_callback(msg)

                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    logging.error(f"API Error: {e}")
                    raise

        raise RuntimeError("Max retries reached")
