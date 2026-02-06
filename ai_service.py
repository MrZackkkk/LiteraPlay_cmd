import time
import logging
from typing import Optional, Callable
from google import genai
from google.genai import types

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
            logging.info("GenAI Client initialized.")
        except Exception as e:
            logging.error(f"Failed to initialize GenAI client: {e}")
            raise

    def create_chat(self, system_instruction: str):
        """Creates a new chat session with the given system instruction."""
        if not self.client:
            raise RuntimeError("Client not initialized")

        try:
            config = types.GenerateContentConfig(
                temperature=0.7,
                system_instruction=system_instruction
            )
            chat = self.client.chats.create(
                model=self.model_name,
                config=config,
                history=[]
            )
            return chat
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
                return response.text
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
                    raise e

        raise RuntimeError("Max retries reached")
