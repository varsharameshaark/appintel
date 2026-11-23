
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
    available_tools = session.tools()

    # Find the multi-execution tool
    execute_tool = next(
        tool for tool in available_tools
        if tool.__name__ == "COMPOSIO_MULTI_EXECUTE_TOOL"
    )

    print("Executing Salesforce documentation searches...")

    result = execute_tool(
        tools=[
            {
                "tool_slug": "SEARCH1API_SEARCH_WEB",
                "arguments": {
                    "requests": [
                        {
                            "query": (
                                "site:developer.salesforce.com/docs "
                                "Salesforce REST API OAuth 2.0 authentication "
                                "developer documentation"
                            ),
                            "search_service": "google",
                            "max_results": 5,
                            "crawl_results": 2,
                            "include_sites": [
                                "developer.salesforce.com"
                            ]
                        },
                        {
                            "query": (
                                "site:developer.salesforce.com/docs "
                                "Salesforce Hosted MCP Servers documentation"
                            ),
                            "search_service": "google",
                            "max_results": 5,
                            "crawl_results": 2,
                            "include_sites": [
                                "developer.salesforce.com"
                            ]
                        }
                    ]
                }
            }
        ],
        thought=(
            "Research Salesforce using official developer documentation. "
            "Collect evidence about OAuth authentication, API access, "
            "and hosted MCP support."
        ),
        sync_response_to_workbench=False,
        current_step="Searching Salesforce official documentation",
        current_step_metric="1 of 1",
        session_id="page"
    )

    print("\n========== EXECUTION RESULT ==========")
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))

    # Save actual tool execution output
    output_path = root / "data" / "salesforce_search_evidence.json"

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(
            result,
            file,
            indent=2,
            ensure_ascii=False,
            default=str
        )

    print("\nEvidence saved to:", output_path)


if __name__ == "__main__":
    main()
