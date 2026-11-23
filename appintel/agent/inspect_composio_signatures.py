import os
import inspect
from pathlib import Path
from dotenv import load_dotenv
from composio import Composio
from composio_gemini import GeminiProvider
import inspect

from composio import Composio
from composio_gemini import GeminiProvider


def main():

    print("Initializing Composio...")

    ROOT_DIR = Path(__file__).resolve().parent.parent
    load_dotenv(ROOT_DIR / ".env")

    if not os.getenv("COMPOSIO_API_KEY"):
        raise ValueError("COMPOSIO_API_KEY is missing from the .env file")

    composio = Composio(
        provider=GeminiProvider()
    )

    session = composio.create(
        user_id="appintel-local-test"
    )

    tools = session.tools()

    print(f"\nTotal tools: {len(tools)}")

    for index, tool in enumerate(tools, start=1):

        print("\n" + "=" * 60)
        print(f"TOOL {index}")

        print(
            "Name:",
            getattr(tool, "__name__", "Unknown")
        )

        try:
            print(
                "Signature:",
                inspect.signature(tool)
            )
        except Exception as exc:
            print("Signature unavailable:", exc)

        print(
            "Annotations:",
            getattr(tool, "__annotations__", {})
        )

        print(
            "Description:",
            getattr(tool, "__doc__", None)
        )

    print("\nInspection completed.")


if __name__ == "__main__":
    main()
