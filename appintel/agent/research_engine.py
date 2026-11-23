
import json
from pathlib import Path

from models import AppResearch


OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data" / "research"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def validate_and_save(research_data, app):
    """
    Validate research using Pydantic and save one JSON file per app.
    """

    # Until independent evidence verification is implemented,
    # do not allow the LLM to assign High confidence.
    if research_data.get("confidence") == "High":
        research_data["confidence"] = "Medium"

    result = AppResearch.model_validate(research_data)

    # Ensure Gemini researched the requested application
    if result.app_id != app["id"]:
        raise ValueError("Application ID mismatch")

    if result.app_name.lower() != app["name"].lower():
        raise ValueError("Application name mismatch")

    output_path = OUTPUT_DIR / (
        f'{app["id"]:03d}_{app["name"].lower().replace(" ", "_")}.json'
    )

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(
            result.model_dump(),
            file,
            indent=4,
            ensure_ascii=False
        )

    return result, output_path
