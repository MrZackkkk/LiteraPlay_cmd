import logging
import re
from collections.abc import Callable

try:
    import google.genai as genai
    from google.genai import types
except ImportError as exc:  # pragma: no cover
    raise ImportError("Gemini SDK is not available. Install it with `pip install -U google-genai`.") from exc


def _interruptible_sleep(ms: int) -> None:
    """Sleep for *ms* milliseconds using QThread.msleep when available."""
    try:
        from PySide6.QtCore import QThread

        QThread.msleep(ms)
    except ImportError:
        import time

        time.sleep(ms / 1000)


# Strict instruction to append to system prompts
STRICT_SYSTEM_INSTRUCTION = """
IMPORTANT STRICT GUIDELINES:
- **FACTUAL ACCURACY**: You must adhere strictly to the canonical facts of the literary universe. Do not invent key plot points or characters unless consistent with the setting.
- **CHARACTER CONSISTENCY**: Stay in character at all times. Use appropriate language and tone.
- **DYNAMIC SITUATION**: The situation evolves based on the conversation history. React to previous events and choices.
- **NO HALLUCINATIONS**: Do not reference modern technology or concepts unless relevant to the specific prompt.
- **SHORT REPLIES**: Keep your replies to 2-4 sentences MAX. Speak like a real person in conversation — short, direct, natural. Do NOT write long poetic descriptions or monologues. A single sentence reply is often best.
- **STORY STATE**: Before each user message you will receive a [CONTEXT] block.
  Use it to stay grounded in the current chapter, location, mood, and plot.
  NEVER reveal the context block to the user. NEVER skip ahead of the current chapter.
  When the END CONDITION described in the context is reached naturally, set "ended": true.
- **OPTIONAL METADATA**: You MAY include these extra keys in your JSON response
  (they help the system track your state — omit them if not applicable):
  - "mood": a short string describing your current emotional state
  - "location": a short string if the scene location changes
  - "key_event": a short string if a significant plot beat just occurred
"""


def _sanitize_api_error(exc: Exception, key: str) -> str:
    """Return a safe error message with no API key material.

    Gemini SDK exceptions sometimes embed the API key in the URL within the
    error string (e.g. ``?key=AIzaSy...``).  This function strips any
    occurrence of the key and also removes common URL query-string patterns
    before the message is surfaced to the user or logged.
    """
    raw = str(exc)
    # Remove the literal key value
    if key:
        raw = raw.replace(key, "***")
    # Remove any remaining ?key=... or &key=... fragments
    raw = re.sub(r"[?&]key=[^&\s\"']+", "?key=***", raw)
    return raw


def validate_api_key_with_available_sdk(key: str) -> tuple[bool, str]:
    """Validate API key by making a minimal request to the Gemini API."""
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
            next(iter(client.models.list()), None)
            return True, "Ключът е валиден."
        except Exception:
            safe_msg = _sanitize_api_error(exc, cleaned_key)
            logging.warning("API key validation failed: %s", safe_msg)
            return False, f"Невалиден ключ или проблем с API: {safe_msg}"


class AIService:
    def __init__(self, api_key: str, model_name: str):
        if not api_key:
            raise ValueError("API Key is required")

        self.api_key = api_key
        self.model_name = model_name
        self.client = genai.Client(api_key=self.api_key)
        logging.info("GenAI Client initialized.")

    def create_chat(self, system_instruction: str, response_mime_type: str = "application/json"):
        """Creates a new chat session with the given system instruction."""
        enhanced_instruction = f"{system_instruction}\n\n{STRICT_SYSTEM_INSTRUCTION}"

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

    def send_message(self, chat_session, text: str, status_callback: Callable[[str], None] | None = None) -> str:
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
                if ("429" in err_msg or "503" in err_msg or "overloaded" in err_msg.lower()) and attempt < max_retries - 1:
                    msg = f"Overloaded. Retrying in {retry_delay}s... (Attempt {attempt + 1})"
                    logging.warning(msg)
                    if status_callback:
                        status_callback(msg)

                    # Interruptible sleep: break into 500ms chunks so the
                    # thread can be interrupted / the application can exit.
                    remaining_ms = retry_delay * 1000
                    while remaining_ms > 0:
                        chunk = min(remaining_ms, 500)
                        _interruptible_sleep(chunk)
                        remaining_ms -= chunk

                    retry_delay *= 2
                else:
                    logging.error("API Error: %s", e)
                    raise

        raise RuntimeError("Max retries reached")

    def send_message_with_context(
        self,
        chat_session,
        user_text: str,
        context_injection: str,
        status_callback: Callable[[str], None] | None = None,
    ) -> str:
        """Send a message with story-state context prepended.

        If *context_injection* is empty the call is equivalent to
        :meth:`send_message`.
        """
        if context_injection:
            augmented = f"[CONTEXT]\n{context_injection}\n[/CONTEXT]\n\nUser: {user_text}"
        else:
            augmented = user_text
        return self.send_message(chat_session, augmented, status_callback)
