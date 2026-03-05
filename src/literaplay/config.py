import os
import sys
from pathlib import Path

from literaplay.dependency_compat import load_dotenv_functions

load_dotenv, set_key = load_dotenv_functions()


def _get_env_path() -> Path:
    """Return an absolute path to the .env file that works in both development
    and PyInstaller bundle environments.

    - In a PyInstaller one-dir bundle, ``sys.frozen`` is set and
      ``sys._MEIPASS`` points to the temp extraction directory.  The writable
      location adjacent to the executable is ``sys.executable``'s parent.
    - In development the .env lives next to ``pyproject.toml`` (the project
      root), which is two directories above this file
      (``src/literaplay/config.py`` → ``src/literaplay`` → ``src`` → root).
    """
    if getattr(sys, "frozen", False):
        # Running inside a PyInstaller bundle — write next to the executable
        return Path(sys.executable).parent / ".env"
    # Development: project root is three levels up from this file
    return Path(__file__).resolve().parent.parent.parent / ".env"


_ENV_PATH = _get_env_path()

# Load environment variables from the resolved path
load_dotenv(str(_ENV_PATH))

# API Configuration
API_KEY = os.getenv("GOOGLE_API_KEY")
DEFAULT_MODEL = os.getenv("LITERAPLAY_MODEL", "gemini-3-flash-preview")


def save_api_key(key: str, dotenv_path: str | None = None) -> None:
    """Persist API key in .env and update runtime config."""
    cleaned_key = (key or "").strip()
    if not cleaned_key:
        raise ValueError("API key cannot be empty")

    path = dotenv_path if dotenv_path is not None else str(_ENV_PATH)
    set_key(path, "GOOGLE_API_KEY", cleaned_key)

    global API_KEY
    API_KEY = cleaned_key
    os.environ["GOOGLE_API_KEY"] = cleaned_key


def save_model_name(model_name: str, dotenv_path: str | None = None) -> None:
    """Persist model name in .env and update runtime config."""
    cleaned_name = (model_name or "").strip()
    if not cleaned_name:
        raise ValueError("Model name cannot be empty")

    path = dotenv_path if dotenv_path is not None else str(_ENV_PATH)
    set_key(path, "LITERAPLAY_MODEL", cleaned_name)

    global DEFAULT_MODEL
    DEFAULT_MODEL = cleaned_name
    os.environ["LITERAPLAY_MODEL"] = cleaned_name
