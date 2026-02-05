import os
from dotenv import load_dotenv
from google import genai

load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")

if not API_KEY:
    print("Error: GOOGLE_API_KEY not found.")
    exit()

print("Checking models...")
try:
    client = genai.Client(api_key=API_KEY)
    
    print("\n--- AVAILABLE MODELS ---")
    # We will list everything safely without complex filtering
    for model in client.models.list():
        # Depending on the exact SDK version, 'name' or 'display_name' should exist
        name = getattr(model, 'name', None)
        
        # If we found a name, print it
        if name:
            # Clean up the name if it starts with "models/"
            clean_name = name.replace("models/", "")
            print(f"- {clean_name}")

except Exception as e:
    print(f"\nError listing models: {e}")