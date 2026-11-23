
import inspect
from dotenv import load_dotenv
from composio import Composio
from composio_gemini import GeminiProvider

load_dotenv()

composio = Composio(provider=GeminiProvider())
session = composio.create(user_id="appintel-local-test")
tools = session.tools()

print(f"\nTotal tools available: {len(tools)}\n")

for index, tool in enumerate(tools, start=1):
    print(f"\nTOOL {index}")
    print("Name:", getattr(tool, "__name__", "Not available"))
    print("Description:", getattr(tool, "__doc__", "Not available"))
    print("Signature:", inspect.signature(tool))

    metadata = getattr(tool, "__dict__", {})
    print("Metadata:", metadata)
    print("-" * 60)
