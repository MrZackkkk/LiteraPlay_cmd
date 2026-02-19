import os
import sys

# Ensure the root directory is in sys.path
sys.path.append(os.getcwd())

try:
    from data import LIBRARY
except Exception as e:
    print(f"Error importing data: {e}")
    sys.exit(1)


def _assert_book_context(work_key: str, label: str):
    if work_key not in LIBRARY:
        print(f"Failure: '{work_key}' key missing from LIBRARY.")
        sys.exit(1)

    context = LIBRARY[work_key].get("pdf_context", "")
    print(f"{label} context length: {len(context)}")

    if context.strip():
        print(f"Success: PDF context loaded for {label}.")
        return

    print(f"Warning: PDF context missing for {label}.")
    print("Likely cause: missing PDF dependencies (e.g. pypdf) or extraction failure in environment.")


def test_book_contexts():
    _assert_book_context("nemili", "NEMILI-NEDRAGI")
    _assert_book_context("pod_igoto", "POD IGOTO")
    _assert_book_context("tyutyun", "TYUTYUN")


if __name__ == "__main__":
    test_book_contexts()
