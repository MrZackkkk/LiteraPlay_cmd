import os
from pathlib import Path
from literaplay.dependency_compat import load_dotenv_functions

# Project root: two levels up from config.py (src/literaplay/config.py -> project root)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_DOTENV_PATH = str(_PROJECT_ROOT / ".env")

load_dotenv, set_key = load_dotenv_functions()

# Load environment variables
load_dotenv(_DOTENV_PATH)

# API Configuration
API_KEY = os.getenv("GOOGLE_API_KEY")
DEFAULT_MODEL = "gemini-3-flash-preview"

# UI Configuration
WINDOW_SIZE = "600x800"
APPEARANCE_MODE = "Dark"
TITLE = "LiteraPlay - Интерактивна Литература"

# Colors
COLOR_USER_BUBBLE = "#1F6AA5"
COLOR_AI_BUBBLE = "#333333"


def save_api_key(key: str, dotenv_path: str = _DOTENV_PATH):
    """Persist API key in .env and update runtime config."""
    cleaned_key = (key or "").strip()
    if not cleaned_key:
        raise ValueError("API key cannot be empty")

    set_key(dotenv_path, "GOOGLE_API_KEY", cleaned_key)

    global API_KEY
    API_KEY = cleaned_key
