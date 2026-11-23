
import os
import json
from pathlib import Path

from dotenv import load_dotenv
from composio import Composio
from composio_gemini import GeminiProvider


def main():
    # Load environment variables
    root = Path(__file__).resolve().parent.parent
    load_dotenv(root / ".env")

    if not os.getenv("COMPOSIO_API_KEY"):
        raise ValueError("COMPOSIO_API_KEY is missing")

    print("Initializing Composio...")

    composio = Composio(provider=GeminiProvider())
    session = composio.create(user_id="appintel-local-test")
    tools = session.tools()

    # Find the search tool
    search_tool = next(
        tool for tool in tools
        if tool.__name__ == "COMPOSIO_SEARCH_TOOLS"
    )

    print("\nSearching for web research tools...")

    result = search_tool(
        queries=[
            {
                "use_case": (
                    "Find web search and webpage crawling tools "
                    "for researching official SaaS API documentation, "
                    "authentication methods, API access requirements, "
                    "and MCP support."
                ),
                "known_fields": "Preferred source: official documentation"
            }
        ],
        session={"generate_id": True},
        model="",
        search_strategy="auto"
    )

    print("\n========== SEARCH RESULT ==========")
    print(json.dumps(result, indent=2, default=str))

    # Save discovery output for inspection
    output_path = root / "data" / "composio_search_result.json"

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(result, file, indent=2, default=str)

    print("\nSaved search result:", output_path)


if __name__ == "__main__":
    main()
