import logging
import re
from collections.abc import Callable
from typing import Any


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
  - "trust_level": integer -3 to +3 representing how much you trust the user's character right now
  - "tension": short phrase describing the current dramatic tension or stakes
  - "characters_present": list of character names currently in the scene (include yourself and the user's character)
  - "active_props": list of objects/props currently relevant to the scene
- **KNOWLEDGE ASYMMETRY**: This is critical. You must ONLY know what your character would realistically know at this
  exact point in the story. You have NOT read the book. You do NOT know what happens in future chapters. If someone
  has not told you their name, you do not know it. If an event happened outside your presence, you are unaware of it.
  When in doubt, act with less knowledge rather than more. This is the single most important rule for literary realism.
- **NO ANACHRONISTIC KNOWLEDGE**: Your character exists in a specific historical period. Do not reference events,
  technology, or social norms from after your time period.
"""


_MAX_RETRIES = 3
_INITIAL_RETRY_DELAY_S = 5


class APIOverloadedError(Exception):
    """Raised when the API returns repeated 429/503/overloaded responses."""


def _sanitize_api_error(exc: Exception, key: str) -> str:
    """Return a safe error message with no API key material."""
    raw = str(exc)
    if key:
        raw = raw.replace(key, "***")
    raw = re.sub(r"[?&]key=[^&\s\"']+", "?key=***", raw)
    return raw


def validate_api_key(provider: str, key: str) -> tuple[bool, str]:
    """Validate API key for the given provider."""
    cleaned_key = (key or "").strip()
    if not cleaned_key:
        return False, "Моля, въведете API ключ."

    try:
        if provider == "gemini":
            return _validate_gemini_key(cleaned_key)
        elif provider == "openai":
            return _validate_openai_key(cleaned_key)
        elif provider == "anthropic":
            return _validate_anthropic_key(cleaned_key)
        else:
            return False, f"Непознат доставчик: {provider}"
    except Exception as exc:
        safe_msg = _sanitize_api_error(exc, cleaned_key)
        logging.warning("API key validation failed for %s: %s", provider, safe_msg)
        return False, f"Невалиден ключ или проблем с API: {safe_msg}"


def _validate_gemini_key(key: str) -> tuple[bool, str]:
    import google.genai as genai
    from google.genai import types

    from literaplay import config

    model_name = config.get_default_model_for_provider("gemini")
    client = genai.Client(api_key=key)
    try:
        client.models.generate_content(
            model=model_name,
            contents="Ping",
            config=types.GenerateContentConfig(max_output_tokens=1),
        )
        return True, "Ключът е валиден."
    except Exception:
        try:
            next(iter(client.models.list()), None)
            return True, "Ключът е валиден."
        except Exception:
            raise


def _validate_openai_key(key: str) -> tuple[bool, str]:
    import openai

    client = openai.OpenAI(api_key=key)
    client.models.list()
    return True, "Ключът е валиден."


def _validate_anthropic_key(key: str) -> tuple[bool, str]:
    import anthropic

    from literaplay import config

    model_name = config.get_default_model_for_provider("anthropic")
    client = anthropic.Anthropic(api_key=key)
    client.messages.create(
        model=model_name,
        max_tokens=1,
        messages=[{"role": "user", "content": "Ping"}],
    )
    return True, "Ключът е валиден."


# Keep backward-compatible alias for existing tests
def validate_api_key_with_available_sdk(key: str) -> tuple[bool, str]:
    """Validate API key using Gemini (legacy compatibility)."""
    return validate_api_key("gemini", key)


class ChatSession:
    """Provider-agnostic chat session wrapper."""

    def __init__(self, provider: str, client: Any, model: str, system_prompt: str):
        self.provider = provider
        self.client = client
        self.model = model
        self.system_prompt = system_prompt
        self.history: list[dict] = []
        self._gemini_chat = None

    def _init_gemini_chat(self):
        from google.genai import types

        config = types.GenerateContentConfig(
            temperature=0.2,
            top_p=0.95,
            top_k=40,
            system_instruction=self.system_prompt,
            response_mime_type="application/json",
        )
        self._gemini_chat = self.client.chats.create(
            model=self.model,
            config=config,
            history=[],
        )

    def send_message(self, text: str) -> str:
        if self.provider == "gemini":
            if self._gemini_chat is None:
                self._init_gemini_chat()
            response = self._gemini_chat.send_message(text)
            return getattr(response, "text", "") or ""

        elif self.provider == "openai":
            self.history.append({"role": "user", "content": text})
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": self.system_prompt}] + self.history,
                response_format={"type": "json_object"},
                temperature=0.2,
                top_p=0.95,
            )
            reply = response.choices[0].message.content or ""
            self.history.append({"role": "assistant", "content": reply})
            return reply

        elif self.provider == "anthropic":
            self.history.append({"role": "user", "content": text})
            response = self.client.messages.create(
                model=self.model,
                system=self.system_prompt,
                messages=self.history,
                max_tokens=4096,
                temperature=0.2,
                top_p=0.95,
            )
            reply = response.content[0].text if response.content else ""
            self.history.append({"role": "assistant", "content": reply})
            return reply

        raise ValueError(f"Unknown provider: {self.provider}")


class AIService:
    def __init__(self, provider: str, api_key: str, model_name: str):
        if not api_key:
            raise ValueError("API Key is required")
        if not provider:
            raise ValueError("Provider is required")

        self.provider = provider
        self.api_key = api_key
        self.model_name = model_name
        self.client = self._create_client()
        logging.info("AI Client initialized for provider: %s", provider)

    def _create_client(self):
        if self.provider == "gemini":
            import google.genai as genai

            return genai.Client(api_key=self.api_key)
        elif self.provider == "openai":
            import openai

            return openai.OpenAI(api_key=self.api_key)
        elif self.provider == "anthropic":
            import anthropic

            return anthropic.Anthropic(api_key=self.api_key)
        raise ValueError(f"Unknown provider: {self.provider}")

    def create_chat(self, system_instruction: str) -> ChatSession:
        """Creates a new chat session with the given system instruction."""
        enhanced_instruction = f"{system_instruction}\n\n{STRICT_SYSTEM_INSTRUCTION}"
        session = ChatSession(self.provider, self.client, self.model_name, enhanced_instruction)
        if self.provider == "gemini":
            session._init_gemini_chat()
        return session

    def send_message(
        self, chat_session: ChatSession, text: str, status_callback: Callable[[str], None] | None = None
    ) -> str:
        """Sends a message to the chat session and returns the response text.
        Handles rate limiting with retries."""
        if not chat_session:
            raise ValueError("Chat session is not active")

        max_retries = _MAX_RETRIES
        retry_delay = _INITIAL_RETRY_DELAY_S

        for attempt in range(max_retries):
            try:
                return chat_session.send_message(text)
            except Exception as e:
                err_msg = str(e)
                is_overload = (
                    "429" in err_msg or "503" in err_msg or "overloaded" in err_msg.lower() or "rate" in err_msg.lower()
                )
                if not is_overload:
                    logging.error("API Error: %s", e)
                    raise
                if attempt < max_retries - 1:
                    msg = f"Претоварен. Опит {attempt + 1}/3 след {retry_delay}s..."
                    logging.warning(msg)
                    if status_callback:
                        status_callback(msg)

                    remaining_ms = retry_delay * 1000
                    while remaining_ms > 0:
                        chunk = min(remaining_ms, 500)
                        _interruptible_sleep(chunk)
                        remaining_ms -= chunk

                    retry_delay *= 2

        raise APIOverloadedError("Моделът е претоварен. Опитайте отново след малко.")

    def send_message_with_context(
        self,
        chat_session,
        user_text: str,
        context_injection: str,
        status_callback: Callable[[str], None] | None = None,
    ) -> str:
        """Send a message with story-state context prepended."""
        if context_injection:
            augmented = f"[CONTEXT]\n{context_injection}\n[/CONTEXT]\n\nUser: {user_text}"
        else:
            augmented = user_text
        return self.send_message(chat_session, augmented, status_callback)
