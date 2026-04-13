import os
from google import genai
from dotenv import load_dotenv

load_dotenv()
api_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

print("Listing models...")
try:
    models = client.models.list()
    target_model = os.environ.get("GEMINI_MODEL_NAME")
    found = False
    for m in models:
        # No SDK atual, usamos 'supported_actions'
        actions = getattr(m, 'supported_actions', [])
        print(f"Name: {m.name}, Actions: {actions}")
        if target_model in m.name:
            found = True
            
    print("\n--- Model Verification ---")
    if found:
        print(f"SUCCESS: Model '{target_model}' is available and configured correctly.")
    else:
        print(f"WARNING: Model '{target_model}' was NOT found in the listing.")
except Exception as e:
    print(f"Error: {e}")
