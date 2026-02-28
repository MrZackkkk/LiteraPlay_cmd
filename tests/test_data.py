import unittest

from literaplay.data import LIBRARY


class TestData(unittest.TestCase):
    def test_library_structure(self):
        # Ensure library has the expected keys and types
        self.assertIn("pod_igoto", LIBRARY)
        self.assertIn("nemili", LIBRARY)
        self.assertIn("tyutyun", LIBRARY)
        for key, work in LIBRARY.items():
            self.assertIn("title", work, f"Missing 'title' in '{key}'")
            self.assertIn("situations", work, f"Missing 'situations' in '{key}'")
            self.assertIsInstance(work["situations"], list)
            self.assertGreater(len(work["situations"]), 0, f"'{key}' has no situations")

    def test_situations_have_required_keys(self):
        required = {"key", "title", "character", "prompt", "intro", "first_message"}
        for work_key, work in LIBRARY.items():
            for i, sit in enumerate(work["situations"]):
                for rk in required:
                    self.assertIn(rk, sit, f"Missing '{rk}' in situations[{i}] of '{work_key}'")

    def test_situations_have_choices_list(self):
        for work_key, work in LIBRARY.items():
            for i, sit in enumerate(work["situations"]):
                choices = sit.get("choices", [])
                self.assertIsInstance(choices, list, f"'choices' is not a list in situations[{i}] of '{work_key}'")

    def test_pod_igoto_situations_have_chapters(self):
        work = LIBRARY["pod_igoto"]
        for i, sit in enumerate(work["situations"]):
            self.assertIn("chapters", sit, f"Missing 'chapters' in pod_igoto situations[{i}]")
            chapters = sit["chapters"]
            self.assertIsInstance(chapters, list)
            self.assertGreater(len(chapters), 0)

    def test_chapter_fields_valid(self):
        required_keys = {"id", "title", "setting", "character_mood", "plot_summary", "end_condition"}
        for work_key, work in LIBRARY.items():
            for sit in work.get("situations", []):
                for i, ch in enumerate(sit.get("chapters", [])):
                    for rk in required_keys:
                        self.assertIn(rk, ch, f"Missing '{rk}' in chapters[{i}] of '{work_key}/{sit.get('key', '?')}'")
                    self.assertIsInstance(ch.get("max_turns", 20), int)


if __name__ == "__main__":
    unittest.main()
