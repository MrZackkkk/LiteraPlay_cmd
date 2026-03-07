"""Tests for book_loader module."""

import tempfile
import textwrap
import unittest
from pathlib import Path

from literaplay.book_loader import BookTextIndex, get_chapter_excerpt, load_book_texts, load_library


class TestLoadLibrary(unittest.TestCase):
    """Tests for load_library YAML loading."""

    def test_loads_real_books(self):
        """Smoke test: load the actual books/ directory."""
        books_dir = Path(__file__).resolve().parent.parent / "books"
        library = load_library(books_dir)
        self.assertIn("pod_igoto", library)
        self.assertIn("nemili", library)
        self.assertIn("tyutyun", library)

    def test_situations_have_common_rules_in_prompt(self):
        """COMMON_RULES should be prepended to every prompt."""
        from literaplay.data import COMMON_RULES

        books_dir = Path(__file__).resolve().parent.parent / "books"
        library = load_library(books_dir)
        for work_key, work in library.items():
            for sit in work["situations"]:
                self.assertTrue(
                    sit["prompt"].startswith(COMMON_RULES),
                    f"Prompt in {work_key}/{sit['key']} does not start with COMMON_RULES",
                )

    def test_validates_missing_keys(self):
        """Should raise ValueError for malformed YAML."""
        with tempfile.TemporaryDirectory() as tmp:
            book_dir = Path(tmp) / "test_book"
            book_dir.mkdir()
            meta = book_dir / "meta.yaml"
            meta.write_text("title: Test\n")  # missing color, situations
            with self.assertRaises(ValueError):
                load_library(Path(tmp))

    def test_validates_situation_keys(self):
        """Should raise ValueError for situations missing required keys."""
        with tempfile.TemporaryDirectory() as tmp:
            book_dir = Path(tmp) / "test_book"
            book_dir.mkdir()
            meta = book_dir / "meta.yaml"
            meta.write_text(
                textwrap.dedent("""\
                title: Test
                color: "#000"
                situations:
                  - key: test
                    title: Test Sit
            """)
            )
            with self.assertRaises(ValueError):
                load_library(Path(tmp))


class TestBookTextIndex(unittest.TestCase):
    """Tests for BookTextIndex chapter parsing."""

    def _write_text_md(self, tmp_dir, content):
        p = Path(tmp_dir) / "text.md"
        p.write_text(content, encoding="utf-8")
        return p

    def test_splits_by_headers(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = self._write_text_md(tmp, "## Chapter 1\nHello\n## Chapter 2\nWorld\n")
            idx = BookTextIndex(p)
            self.assertEqual(idx.get_excerpt("Chapter 1"), "Hello")
            self.assertEqual(idx.get_excerpt("Chapter 2"), "World")

    def test_truncates_to_max_chars(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = self._write_text_md(tmp, "## Ch\n" + "x" * 5000 + "\n")
            idx = BookTextIndex(p)
            excerpt = idx.get_excerpt("Ch", max_chars=100)
            self.assertEqual(len(excerpt), 100)

    def test_missing_chapter_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = self._write_text_md(tmp, "## Ch\ntext\n")
            idx = BookTextIndex(p)
            self.assertEqual(idx.get_excerpt("Nonexistent"), "")

    def test_real_pod_igoto_chapters(self):
        """Verify real book text is parseable."""
        text_path = Path(__file__).resolve().parent.parent / "books" / "pod_igoto" / "text.md"
        if text_path.exists():
            idx = BookTextIndex(text_path)
            excerpt = idx.get_excerpt("I. Гост")
            self.assertGreater(len(excerpt), 100)
            self.assertIn("Марко", excerpt)


class TestGetChapterExcerpt(unittest.TestCase):
    """Tests for get_chapter_excerpt helper."""

    def test_returns_excerpt_when_mapping_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "text.md"
            p.write_text("## I. Test\nSome text here\n", encoding="utf-8")
            book_texts = {"test": BookTextIndex(p)}
            chapters = [{"id": "ch1", "text_chapter": "I. Test"}]
            result = get_chapter_excerpt(book_texts, "test", "ch1", chapters)
            self.assertEqual(result, "Some text here")

    def test_returns_empty_when_no_text_chapter(self):
        chapters = [{"id": "ch1"}]  # no text_chapter field
        result = get_chapter_excerpt({}, "test", "ch1", chapters)
        self.assertEqual(result, "")

    def test_returns_empty_when_book_not_found(self):
        chapters = [{"id": "ch1", "text_chapter": "I. Test"}]
        result = get_chapter_excerpt({}, "missing_book", "ch1", chapters)
        self.assertEqual(result, "")


class TestLoadBookTexts(unittest.TestCase):
    def test_loads_real_books(self):
        books_dir = Path(__file__).resolve().parent.parent / "books"
        texts = load_book_texts(books_dir)
        self.assertIn("pod_igoto", texts)
        self.assertIn("nemili", texts)
        self.assertIn("tyutyun", texts)


if __name__ == "__main__":
    unittest.main()
