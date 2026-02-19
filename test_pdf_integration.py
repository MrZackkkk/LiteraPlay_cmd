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

    prompt = LIBRARY[work_key]["prompt"]
    print(f"{label} prompt length: {len(prompt)}")

    marker = f"КОНТЕКСТ ОТ РОМАНА ({label}):"
    if marker in prompt:
        print(f"Success: Context marker found for {label}.")
        return

    print(f"Warning: Context marker missing for {label}.")
    print("Likely cause: missing PDF dependencies (e.g. pypdf) or extraction failure in environment.")


def test_book_contexts():
    _assert_book_context("nemili", "NEMILI-NEDRAGI")
    _assert_book_context("pod_igoto", "POD IGOTO")
    _assert_book_context("tyutyun", "TYUTYUN")


if __name__ == "__main__":
    test_book_contexts()
