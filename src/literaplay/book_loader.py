from __future__ import annotations

import logging
import sys
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)


def get_books_dir() -> Path:
    """Return the path to the books/ directory, handling PyInstaller bundles."""
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "books"
    return Path(__file__).resolve().parent.parent.parent / "books"


# ---------------------------------------------------------------------------
# YAML loading → LIBRARY dict
# ---------------------------------------------------------------------------

_REQUIRED_WORK_KEYS = {"title", "color", "situations"}
_REQUIRED_SITUATION_KEYS = {"key", "title", "character", "prompt", "intro", "first_message"}


def load_library(books_dir: Path) -> dict:
    """Scan books/*/meta.yaml files and return a combined LIBRARY dict.

    Each work dict is keyed by its directory name (e.g. "pod_igoto").
    COMMON_RULES is prepended to every situation's prompt field.
    Raises ValueError for missing or malformed files.
    """
    from literaplay.data import COMMON_RULES  # lazy import to avoid circular dependency

    library: dict = {}

    for meta_path in sorted(books_dir.glob("*/meta.yaml")):
        book_key = meta_path.parent.name

        try:
            with meta_path.open(encoding="utf-8") as fh:
                work = yaml.safe_load(fh)
        except yaml.YAMLError as exc:
            raise ValueError(f"book_loader: failed to parse {meta_path}: {exc}") from exc

        if not isinstance(work, dict):
            raise ValueError(f"book_loader: {meta_path} must contain a YAML mapping, got {type(work).__name__}")

        missing_work_keys = _REQUIRED_WORK_KEYS - work.keys()
        if missing_work_keys:
            raise ValueError(f"book_loader: {meta_path} is missing required keys: {sorted(missing_work_keys)}")

        situations = work.get("situations")
        if not isinstance(situations, list) or not situations:
            raise ValueError(f"book_loader: {meta_path} 'situations' must be a non-empty list")

        for idx, situation in enumerate(situations):
            if not isinstance(situation, dict):
                raise ValueError(f"book_loader: {meta_path} situation[{idx}] must be a mapping")

            missing_sit_keys = _REQUIRED_SITUATION_KEYS - situation.keys()
            if missing_sit_keys:
                raise ValueError(
                    f"book_loader: {meta_path} situation[{idx}] is missing required keys: {sorted(missing_sit_keys)}"
                )

            raw_prompt = situation["prompt"]
            situation["prompt"] = f"{COMMON_RULES}\n\n{raw_prompt}"

        library[book_key] = work

    return library


# ---------------------------------------------------------------------------
# Chapter text parsing → excerpt injection
# ---------------------------------------------------------------------------


class BookTextIndex:
    """Index of chapter excerpts parsed from a text.md file.

    Chapters are split by '## ' headers. The text under each header is stored
    keyed by the header title (without the '## ' prefix).
    """

    def __init__(self, text_path: Path) -> None:
        self._chapters: dict[str, str] = {}
        self._parse(text_path)

    def _parse(self, text_path: Path) -> None:
        content = text_path.read_text(encoding="utf-8")
        current_title: str | None = None
        current_lines: list[str] = []

        for line in content.splitlines(keepends=True):
            if line.startswith("## "):
                if current_title is not None:
                    self._chapters[current_title] = "".join(current_lines).strip()
                current_title = line[3:].rstrip("\n").strip()
                current_lines = []
            else:
                if current_title is not None:
                    current_lines.append(line)

        if current_title is not None:
            self._chapters[current_title] = "".join(current_lines).strip()

    def get_excerpt(self, chapter_title: str, max_chars: int = 4000) -> str:
        """Return text for chapter_title, truncated to max_chars. Returns '' if not found."""
        text = self._chapters.get(chapter_title, "")
        return text[:max_chars]


def load_book_texts(books_dir: Path) -> dict[str, BookTextIndex]:
    """Scan books/*/text.md files and return a dict of BookTextIndex keyed by directory name."""
    book_texts: dict[str, BookTextIndex] = {}

    for text_path in sorted(books_dir.glob("*/text.md")):
        book_key = text_path.parent.name
        try:
            book_texts[book_key] = BookTextIndex(text_path)
        except OSError as exc:
            logger.warning("book_loader: could not read %s: %s", text_path, exc)

    return book_texts


def get_chapter_excerpt(
    book_texts: dict[str, BookTextIndex],
    book_key: str,
    chapter_id: str,
    chapters: list[dict],
    max_chars: int = 4000,
) -> str:
    """Return the text excerpt for a chapter, or '' if unavailable.

    Finds the chapter dict with matching 'id' in chapters, reads its
    'text_chapter' field, then delegates to BookTextIndex.get_excerpt().
    """
    if book_key not in book_texts:
        return ""

    chapter_def = next((ch for ch in chapters if ch.get("id") == chapter_id), None)
    if chapter_def is None:
        logger.warning("book_loader: chapter id %r not found in chapters list for book %r", chapter_id, book_key)
        return ""

    text_chapter = chapter_def.get("text_chapter")
    if not text_chapter:
        return ""

    return book_texts[book_key].get_excerpt(text_chapter, max_chars)
