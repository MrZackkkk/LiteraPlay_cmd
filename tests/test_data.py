import unittest
import tempfile
import os

from literaplay.data import load_text_content, LIBRARY

class TestData(unittest.TestCase):
    def test_load_text_content_not_found(self):
        result = load_text_content("not_a_real_path.txt")
        self.assertEqual(result, "")

    def test_load_text_content_success(self):
        # Create a temp file to test reading
        with tempfile.NamedTemporaryFile(delete=False, mode='w', encoding='utf-8') as tmp:
            tmp.write("Hello Data!")
            tmp_path = tmp.name

        try:
            result = load_text_content(tmp_path)
            self.assertEqual(result, "Hello Data!")
        finally:
            os.remove(tmp_path)

    def test_library_structure(self):
        # Ensure library has the expected keys and types
        self.assertIn("pod_igoto", LIBRARY)
        self.assertIn("nemili", LIBRARY)
        self.assertIn("title", LIBRARY["nemili"])
        self.assertIsInstance(LIBRARY["nemili"]["choices"], list)

if __name__ == "__main__":
    unittest.main()
