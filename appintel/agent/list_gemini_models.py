
from pathlib import Path
from dotenv import load_dotenv
from google import genai

root = Path(__file__).resolve().parent.parent
load_dotenv(root / ".env")

client = genai.Client()

print("Checking Gemini models available to this API key...\n")

for model in client.models.list():
    name = model.name or ""
    actions = model.supported_actions or []

    if "generateContent" in actions:
        print(f"Model: {name}")
        print(f"Supported actions: {actions}")
        print("-" * 50)
