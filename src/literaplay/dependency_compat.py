"""Helpers for optional third-party dependencies.

This module keeps imports lazy so static analyzers don't report missing imports
in environments where optional UI/config packages are not installed.
"""

from __future__ import annotations

from importlib import import_module
from pathlib import Path
from typing import Callable


def load_dotenv_functions() -> tuple[Callable[[], bool], Callable[[str, str, str], tuple[bool, str, str]]]:
    """Return (load_dotenv, set_key).

    Falls back to lightweight local implementations when python-dotenv
    is unavailable.
    """
    try:
        dotenv = import_module("dotenv")
        return dotenv.load_dotenv, dotenv.set_key
    except ModuleNotFoundError:
        return _fallback_load_dotenv, _fallback_set_key


def _fallback_load_dotenv(dotenv_path: str = ".env") -> bool:
    env_file = Path(dotenv_path)
    if not env_file.exists():
        return False

    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            import os

            os.environ.setdefault(key, value)

    return True


def _fallback_set_key(dotenv_path: str, key: str, value: str):
    env_file = Path(dotenv_path)
    lines = []

    if env_file.exists():
        lines = env_file.read_text(encoding="utf-8").splitlines()

    key_prefix = f"{key}="
    new_line = f'{key}="{value}"'
    replaced = False
    for i, line in enumerate(lines):
        if line.startswith(key_prefix):
            lines[i] = new_line
            replaced = True
            break

    if not replaced:
        lines.append(new_line)

    env_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return True, key, value
