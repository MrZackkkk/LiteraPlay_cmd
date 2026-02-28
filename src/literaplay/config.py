import os
from literaplay.dependency_compat import load_dotenv_functions

load_dotenv, set_key = load_dotenv_functions()

# Load environment variables
load_dotenv()

# API Configuration
API_KEY = os.getenv("GOOGLE_API_KEY")
DEFAULT_MODEL = "gemini-3-flash-preview"


def save_api_key(key: str, dotenv_path: str = ".env"):
    """Persist API key in .env and update runtime config."""
    cleaned_key = (key or "").strip()
    if not cleaned_key:
        raise ValueError("API key cannot be empty")

    set_key(dotenv_path, "GOOGLE_API_KEY", cleaned_key)

    global API_KEY
    API_KEY = cleaned_key
    os.environ["GOOGLE_API_KEY"] = cleaned_key
