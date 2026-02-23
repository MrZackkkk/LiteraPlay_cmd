import unittest
import os
from unittest.mock import patch, MagicMock

from literaplay.pdf_loader import extract_text_from_pdf

class TestPdfLoader(unittest.TestCase):
    def test_file_not_found(self):
        # When file does not exist, should print error and return ""
        result = extract_text_from_pdf("fake_non_existent.pdf")
        self.assertEqual(result, "")

    @patch("literaplay.pdf_loader.os.path.exists")
    @patch("literaplay.pdf_loader.pypdf.PdfReader")
    def test_extract_success(self, mock_reader_cls, mock_exists):
        mock_exists.return_value = True

        mock_page1 = MagicMock()
        mock_page1.extract_text.return_value = "Hello "
        mock_page2 = MagicMock()
        mock_page2.extract_text.return_value = "World!"
        mock_page3 = MagicMock()
        mock_page3.extract_text.return_value = "" # Edge case: no text

        mock_reader_instance = MagicMock()
        mock_reader_instance.pages = [mock_page1, mock_page2, mock_page3]
        mock_reader_cls.return_value = mock_reader_instance

        result = extract_text_from_pdf("dummy.pdf")
        self.assertEqual(result, "Hello \nWorld!")

    @patch("literaplay.pdf_loader.os.path.exists")
    @patch("literaplay.pdf_loader.pypdf.PdfReader")
    def test_extract_exception(self, mock_reader_cls, mock_exists):
        mock_exists.return_value = True
        mock_reader_cls.side_effect = Exception("Read Error")

        result = extract_text_from_pdf("dummy.pdf")
        self.assertEqual(result, "")

if __name__ == "__main__":
    unittest.main()
