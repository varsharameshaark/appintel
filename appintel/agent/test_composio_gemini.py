
import os
from dotenv import load_dotenv
from composio import Composio
from composio_gemini import GeminiProvider
from google import genai
from google.genai import types

load_dotenv()

required = ["COMPOSIO_API_KEY", "GOOGLE_API_KEY"]
missing = [name for name in required if not os.getenv(name)]

if missing:
    raise SystemExit("Missing environment variables: " + ", ".join(missing))

print("1/4 Environment variables detected (values hidden).")

try:
    composio = Composio(provider=GeminiProvider())
    print("2/4 Composio Gemini provider initialized.")

    session = composio.create(user_id="appintel-local-test")
    tools = session.tools()
    print(f"3/4 Composio session created; {len(tools)} tool(s) exposed to Gemini.")

    client = genai.Client()
    config = types.GenerateContentConfig(tools=tools)

    chat = client.chats.create(
        model="gemini-3.5-flash-lite",
        config=config
    )

    
    response = chat.send_message(
    "Use COMPOSIO_MANAGE_CONNECTIONS to verify the existing "
    "connection for the exact toolkit slug 'search1api'. "
    "Set reinitiate_all to false. "
    "Do not create a new connection. "
    "Return the exact connection status."
    )

    print("4/4 Connection result:")
    print(response.text or "(No plain-text response; inspect tool execution logs.)")

except Exception as exc:
    print(f"Integration test failed: {type(exc).__name__}: {exc}")
    raise
