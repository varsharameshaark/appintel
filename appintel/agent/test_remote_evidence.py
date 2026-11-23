import os
from pathlib import Path

from dotenv import load_dotenv
from composio import Composio
from composio_gemini import GeminiProvider


ROOT = Path(__file__).resolve().parent.parent
SESSION_ID = "page"


def main():
    load_dotenv(ROOT / ".env")

    print("Initializing Composio...")

    composio = Composio(provider=GeminiProvider())
    session = composio.create(user_id="appintel-local-test")
    available_tools = session.tools()

    workbench = next(
        (
            tool for tool in available_tools
            if tool.__name__ == "COMPOSIO_REMOTE_WORKBENCH"
        ),
        None
    )

    bash_tool = next(
        (
            tool for tool in available_tools
            if tool.__name__ == "COMPOSIO_REMOTE_BASH_TOOL"
        ),
        None
    )

    if workbench is None:
        raise RuntimeError("Remote workbench tool not found.")

    print("Remote workbench found.")
    print("Inspecting Twenty evidence file...")

    code = """
import json

path = "/mnt/files/mex/once.json"

with open(path, "r", encoding="utf-8") as file:
    data = json.load(file)

print("Top-level keys:", list(data.keys()))

results = data.get("results", [])

for execution in results:
    response = execution.get("response", {})
    print("Response keys:", list(response.keys()))

    actual_data = response.get("data", {})
    print("Actual data keys:", list(actual_data.keys()))

    for query_result in actual_data.get("results", []):
        result_data = query_result.get("data", {})

        for item in result_data.get("results", []):
            print({
                "title": item.get("title", ""),
                "url": item.get("link", ""),
                "snippet": item.get("snippet", ""),
                "has_content": bool(item.get("content"))
            })
"""

    result = workbench(
        code_to_execute=code,
        thought=(
            "Inspect the already saved Twenty search response "
            "and extract its evidence URLs and metadata. "
            "Do not perform another web search."
        ),
        current_step="Inspecting Twenty remote evidence",
        current_step_metric="1 of 1",
        session_id=SESSION_ID
    )

    print("\nREMOTE WORKBENCH RESPONSE:")
    print(result)

    if bash_tool is not None:
        print("Remote bash found. Listing /mnt/files/mex...")
        bash_result = bash_tool(
            command="find /mnt/files/mex -maxdepth 1 -type f -print 2>/dev/null; ls -la /mnt/files/mex 2>/dev/null",
            session_id=SESSION_ID
        )
        print("\nREMOTE BASH RESULT:")
        print(bash_result)


if __name__ == "__main__":
    main()
