import unittest

from literaplay.data import LIBRARY

class TestData(unittest.TestCase):
    def test_library_structure(self):
        # Ensure library has the expected keys and types
        self.assertIn("pod_igoto", LIBRARY)
        self.assertIn("nemili", LIBRARY)
        self.assertIn("title", LIBRARY["nemili"])
        self.assertIsInstance(LIBRARY["nemili"]["choices"], list)

if __name__ == "__main__":
    unittest.main()
