import pypdf
import os

def extract_text_from_pdf(file_path: str) -> str:
    """Extracts text from a PDF file."""
    if not os.path.exists(file_path):
        print(f"PDF file not found: {file_path}")
        return ""

    try:
        reader = pypdf.PdfReader(file_path)
        text = ""
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"
        return text.strip()
    except Exception as e:
        print(f"Error reading PDF {file_path}: {e}")
        return ""
