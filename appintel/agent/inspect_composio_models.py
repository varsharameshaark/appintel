
import inspect
import os
from pathlib import Path
from typing import get_args

from composio import Composio
from composio_gemini import GeminiProvider
from dotenv import load_dotenv


def inspect_annotation(annotation):
    """Inspect Pydantic model types inside an annotation."""
    print("\nAnnotation:", annotation)

    model_classes = get_args(annotation)

    if not model_classes and inspect.isclass(annotation):
        model_classes = (annotation,)

    for model_class in model_classes:
        print("Underlying type:", model_class)

        if not inspect.isclass(model_class):
            continue

        print("Class name:", model_class.__name__)
        inspect_model(model_class)


def inspect_model(model_class):
    """Print fields of a Pydantic model."""
    if hasattr(model_class, "model_fields"):
        print("\nPydantic model fields:")

        for name, field in model_class.model_fields.items():
            print(f"  {name}: {field.annotation}")
            print(f"    Required: {field.is_required()}")
            print(f"    Default: {field.default}")

    elif hasattr(model_class, "__fields__"):
        print("\nModel fields:")

        for name, field in model_class.__fields__.items():
            print(f"  {name}: {field.outer_type_}")


def main():
    print("Initializing Composio...")

    # Load environment variables
    root = Path(__file__).resolve().parent.parent
    load_dotenv(root / ".env")

    if not os.getenv("COMPOSIO_API_KEY"):
        raise ValueError(
            "COMPOSIO_API_KEY is missing from the project .env file"
        )

    # Initialize Composio
    composio = Composio(provider=GeminiProvider())
    session = composio.create(user_id="appintel-local-test")
    tools = session.tools()

    print(f"\nTotal tools: {len(tools)}")

    # Inspect search and execution tools
    for tool in tools:
        if tool.__name__ not in [
            "COMPOSIO_SEARCH_TOOLS",
            "COMPOSIO_MULTI_EXECUTE_TOOL",
        ]:
            continue

        print("\n" + "=" * 70)
        print("TOOL:", tool.__name__)

        annotations = getattr(tool, "__annotations__", {})

        for parameter, annotation in annotations.items():
            if parameter == "return":
                continue

            print("\nPARAMETER:", parameter)
            inspect_annotation(annotation)

    # Inspect the session model separately
    print("\n" + "=" * 70)
    print("INSPECTING SEARCH SESSION MODEL")

    search_tool = next(
        tool for tool in tools
        if tool.__name__ == "COMPOSIO_SEARCH_TOOLS"
    )

    session_annotation = search_tool.__annotations__.get("session")

    if session_annotation:
        inspect_annotation(session_annotation)
    else:
        print("Session annotation not found.")

    print("\nModel inspection completed.")


if __name__ == "__main__":
    main()
