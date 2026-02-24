import logging
import time
from typing import Callable, Optional

try:
    import google.genai as genai
    from google.genai import types
except ImportError as exc:  # pragma: no cover
    raise RuntimeError(
        "Gemini SDK is not available. Install it with `pip install -U google-genai`."
    ) from exc


# Strict instruction to append to system prompts
STRICT_SYSTEM_INSTRUCTION = """
IMPORTANT STRICT GUIDELINES:
- **FACTUAL ACCURACY**: You must adhere strictly to the canonical facts of the literary universe. Do not invent key plot points or characters unless consistent with the setting.
- **CHARACTER CONSISTENCY**: Stay in character at all times. Use appropriate language and tone.
- **DYNAMIC SITUATION**: The situation evolves based on the conversation history. React to previous events and choices.
- **NO HALLUCINATIONS**: Do not reference modern technology or concepts unless relevant to the specific prompt.
"""


def validate_api_key_with_available_sdk(key: str) -> tuple[bool, str]:
    """Validate an API key by making a minimal Gemini API request."""
    cleaned_key = (key or "").strip()
    if not cleaned_key:
        return False, "Моля, въведете API ключ."

    from literaplay import config
    model_name = config.DEFAULT_MODEL

    try:
        client = genai.Client(api_key=cleaned_key)
        client.models.generate_content(
            model=model_name,
            contents="Ping",
            config=types.GenerateContentConfig(max_output_tokens=1),
        )
        return True, "Ключът е валиден."
    except Exception as exc:
        try:
            # Fallback: if generation is blocked, try model listing.
            next(iter(client.models.list()), None)
            return True, "Ключът е валиден."
        except Exception:
            return False, f"Невалиден ключ или проблем с API: {exc}"


class AIService:
    def __init__(self, api_key: str, model_name: str):
        if not api_key:
            raise ValueError("API Key is required")

        self.api_key = api_key
        self.model_name = model_name
        self.client = None
        self._init_client()

    def _init_client(self):
        try:
            self.client = genai.Client(api_key=self.api_key)
            logging.info("GenAI Client initialized (google-genai).")
        except Exception as e:
            logging.error(f"Failed to initialize GenAI client: {e}")
            raise

    def create_chat(self, system_instruction: str, response_mime_type: str = "application/json"):
        """Creates a new chat session with the given system instruction."""
        if not self.client:
            raise RuntimeError("Client not initialized")

        enhanced_instruction = f"{system_instruction}\n\n{STRICT_SYSTEM_INSTRUCTION}"

        try:
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

        max_retries = 5
        retry_delay = 5

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
