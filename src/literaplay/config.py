import json
import os
import sys
from pathlib import Path

from literaplay.dependency_compat import load_dotenv_functions

load_dotenv, set_key = load_dotenv_functions()

PROVIDER_MODELS = {
    "openai": {
        "default": "gpt-4.1-mini",
        "models": [
            {"value": "gpt-4.1-mini", "label": "GPT-4.1 Mini (Default)"},
            {"value": "gpt-4.1", "label": "GPT-4.1"},
            {"value": "gpt-4.1-nano", "label": "GPT-4.1 Nano"},
            {"value": "o4-mini", "label": "o4-mini"},
            {"value": "o3", "label": "o3"},
        ],
    },
    "gemini": {
        "default": "gemini-2.5-flash",
        "models": [
            {"value": "gemini-2.5-flash", "label": "Gemini 2.5 Flash (Default)"},
            {"value": "gemini-2.5-pro", "label": "Gemini 2.5 Pro"},
            {"value": "gemini-3-flash-preview", "label": "Gemini 3 Flash Preview"},
        ],
    },
    "anthropic": {
        "default": "claude-sonnet-4-6",
        "models": [
            {"value": "claude-sonnet-4-6", "label": "Claude Sonnet 4.6 (Default)"},
            {"value": "claude-opus-4-6", "label": "Claude Opus 4.6"},
            {"value": "claude-haiku-4-5", "label": "Claude Haiku 4.5"},
        ],
    },
}


def _get_env_path() -> Path:
    """Return an absolute path to the .env file that works in both development
    and PyInstaller bundle environments."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent / ".env"
    return Path(__file__).resolve().parent.parent.parent / ".env"


_ENV_PATH = _get_env_path()

# Load environment variables from the resolved path
load_dotenv(str(_ENV_PATH))

# Provider selection
PROVIDER = os.getenv("LITERAPLAY_PROVIDER", "")

# API key: prefer new generic key, fall back to legacy Google key
API_KEY = os.getenv("LITERAPLAY_API_KEY") or os.getenv("GOOGLE_API_KEY")

# Backward compat: if we have a key from GOOGLE_API_KEY but no explicit provider, assume gemini
if API_KEY and not PROVIDER and os.getenv("GOOGLE_API_KEY"):
    PROVIDER = "gemini"

# Model: default depends on provider
_raw_model = os.getenv("LITERAPLAY_MODEL", "")
if _raw_model:
    DEFAULT_MODEL = _raw_model
elif PROVIDER and PROVIDER in PROVIDER_MODELS:
    DEFAULT_MODEL = PROVIDER_MODELS[PROVIDER]["default"]
else:
    DEFAULT_MODEL = ""


def get_default_model_for_provider(provider: str) -> str:
    """Return the default model name for the given provider."""
    return PROVIDER_MODELS.get(provider, {}).get("default", "")


def get_models_json(provider: str) -> str:
    """Return JSON string with the model list for a provider."""
    info = PROVIDER_MODELS.get(provider, {"default": "", "models": []})
    return json.dumps(info)


def save_provider(provider: str, dotenv_path: str | None = None) -> None:
    """Persist provider choice in .env and update runtime config."""
    cleaned = (provider or "").strip().lower()
    if cleaned not in PROVIDER_MODELS:
        raise ValueError(f"Unknown provider: {cleaned}")

    path = dotenv_path if dotenv_path is not None else str(_ENV_PATH)
    set_key(path, "LITERAPLAY_PROVIDER", cleaned)

    global PROVIDER
    PROVIDER = cleaned
    os.environ["LITERAPLAY_PROVIDER"] = cleaned


def save_api_key(key: str, dotenv_path: str | None = None) -> None:
    """Persist API key in .env and update runtime config."""
    cleaned_key = (key or "").strip()
    if not cleaned_key:
        raise ValueError("API key cannot be empty")

    path = dotenv_path if dotenv_path is not None else str(_ENV_PATH)
    set_key(path, "LITERAPLAY_API_KEY", cleaned_key)

    global API_KEY
    API_KEY = cleaned_key
    os.environ["LITERAPLAY_API_KEY"] = cleaned_key


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
