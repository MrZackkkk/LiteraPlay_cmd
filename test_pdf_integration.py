import sys
import os

# Ensure the root directory is in sys.path
sys.path.append(os.getcwd())

try:
    from data import LIBRARY
except Exception as e:
    print(f"Error importing data: {e}")
    sys.exit(1)

def test_pod_igoto_context():
    if "pod_igoto" not in LIBRARY:
        print("Failure: 'pod_igoto' key missing from LIBRARY.")
        sys.exit(1)

    prompt = LIBRARY["pod_igoto"]["prompt"]
    print(f"Prompt length: {len(prompt)}")

    if "КОНТЕКСТ ОТ РОМАНА (POD IGOTO):" in prompt:
        print("Success: Context marker found.")
    else:
        print("Failure: Context marker not found.")
        sys.exit(1)

    if len(prompt) > 5000: # Arbitrary large number, book should be much larger
        print("Success: Prompt length indicates PDF content loaded.")
    else:
        print("Failure: Prompt length too short.")
        sys.exit(1)

if __name__ == "__main__":
    test_pod_igoto_context()
