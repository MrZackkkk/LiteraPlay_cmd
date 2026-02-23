import sys
from pathlib import Path

# Allow direct execution from IDEs
_src_dir = Path(__file__).resolve().parent.parent
if str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))

from literaplay import config

def main():
    try:
        import google.genai as genai
    except ImportError as exc:
        print(
            "Error: google-genai SDK is not available. "
            "Install/update it with `pip install -U google-genai` and remove "
            "a conflicting `google` package if present."
        )
        raise SystemExit(1) from exc

    if not config.API_KEY:
        print("Error: GOOGLE_API_KEY not found in config.")
        exit()

    print("Checking models...")
    try:
        client = genai.Client(api_key=config.API_KEY)

        print("\n--- AVAILABLE MODELS ---")
        for model in client.models.list():
            name = getattr(model, "name", None)
            if name:
                clean_name = name.replace("models/", "")
                print(f"- {clean_name}")

    except Exception as e:
        print(f"\nError listing models: {e}")

if __name__ == "__main__":
    main()
