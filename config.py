import os
from dependency_compat import load_customtkinter, load_dotenv_functions

load_dotenv, set_key = load_dotenv_functions()
ctk = load_customtkinter()

# Load environment variables
load_dotenv()

# API Configuration
API_KEY = os.getenv("GOOGLE_API_KEY")
DEFAULT_MODEL = "gemini-3-flash-preview"  # Updated to a stable model name, or keep what was there

# UI Configuration
WINDOW_SIZE = "600x800"
APPEARANCE_MODE = "Dark"
TITLE = "LiteraPlay - Интерактивна Литература"

# Colors
COLOR_USER_BUBBLE = "#1F6AA5"
COLOR_AI_BUBBLE = "#333333"


def setup_appearance():
    ctk.set_appearance_mode(APPEARANCE_MODE)


def save_api_key(key: str, dotenv_path: str = ".env"):
    """Persist API key in .env and update runtime config."""
    cleaned_key = (key or "").strip()
    if not cleaned_key:
        raise ValueError("API key cannot be empty")

    set_key(dotenv_path, "GOOGLE_API_KEY", cleaned_key)

    global API_KEY
    API_KEY = cleaned_key
