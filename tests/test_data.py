import unittest

from literaplay.data import LIBRARY


class TestData(unittest.TestCase):
    def test_library_structure(self):
        # Ensure library has the expected keys and types
        self.assertIn("pod_igoto", LIBRARY)
        self.assertIn("nemili", LIBRARY)
        self.assertIn("title", LIBRARY["nemili"])
        self.assertIsInstance(LIBRARY["nemili"]["choices"], list)

    def test_pod_igoto_has_chapters(self):
        work = LIBRARY["pod_igoto"]
        self.assertIn("chapters", work)
        chapters = work["chapters"]
        self.assertIsInstance(chapters, list)
        self.assertGreater(len(chapters), 0)

    def test_chapter_fields_valid(self):
        required_keys = {"id", "title", "setting", "character_mood",
                         "plot_summary", "end_condition"}
        for key, work in LIBRARY.items():
            for i, ch in enumerate(work.get("chapters", [])):
                for rk in required_keys:
                    self.assertIn(rk, ch,
                                  f"Missing '{rk}' in chapters[{i}] of '{key}'")
                self.assertIsInstance(ch.get("max_turns", 20), int)

    def test_works_without_chapters_still_valid(self):
        # Works without chapters should still have title and prompt
        for key, work in LIBRARY.items():
            self.assertIn("title", work, f"Missing 'title' in '{key}'")
            self.assertIn("prompt", work, f"Missing 'prompt' in '{key}'")


if __name__ == "__main__":
    unittest.main()
