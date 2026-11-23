import json
import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

from load_dataset import load_apps
from research_engine import validate_and_save


def main():
    root = Path(__file__).resolve().parent.parent
    load_dotenv(root / ".env")

    evidence_path = root / "data" / "salesforce_search_evidence.json"

    if not evidence_path.exists():
        raise FileNotFoundError("Salesforce evidence file not found")

    if not os.getenv("GEMINI_API_KEY"):
        raise ValueError("GEMINI_API_KEY is missing from .env")

    print("Loading Salesforce research evidence...")

    with evidence_path.open("r", encoding="utf-8") as file:
        execution_data = json.load(file)

    # Extract actual search results from Composio response
    evidence_items = []

    for execution in execution_data.get("results", []):
        response = execution.get("response", {})

        if not response.get("successful"):
            continue

        data = response.get("data", {})

        for query_result in data.get("results", []):
            if not query_result.get("success"):
                continue

            for item in query_result.get("data", {}).get("results", []):
                evidence_items.append({
                    "title": item.get("title", ""),
                    "url": item.get("link", ""),
                    "snippet": item.get("snippet", ""),
                    "content": item.get("content", "")
                })

    if not evidence_items:
        raise ValueError("No usable search evidence found")

    print(f"Loaded {len(evidence_items)} evidence items.")

    # Get Salesforce from the application dataset
    apps = load_apps()
    app = next(item for item in apps if item["name"] == "Salesforce")

    # Initialize Gemini without Composio tools.
    # Composio research has already been completed.
    client = genai.Client()

    prompt = f"""
You are a SaaS API research analyst.

Research this application using ONLY the supplied evidence.
Do not invent facts or treat missing evidence as confirmation.

APPLICATION:
{json.dumps(app, indent=2)}

RETRIEVED EVIDENCE:
{json.dumps(evidence_items, indent=2)}

Return one valid JSON object with exactly these fields:

{{
  "app_id": 1,
  "app_name": "Salesforce",
  "category": "CRM and Sales",
  "description": "One-line description",
  "auth_methods": [],
  "credential_access": "Unknown",
  "api_type": [],
  "api_breadth": "Description of API capabilities",
  "mcp_available": "Unknown",
  "mcp_evidence": "Evidence-based explanation",
  "buildability": "Unknown",
  "blocker": "Main implementation blocker",
  "evidence": [
    {{
      "url": "Actual source URL",
      "title": "Actual source title",
      "source_type": "Official",
      "supports": "What this source supports",
      "research_method": "Search",
      "excerpt": "Short factual excerpt or paraphrase"
    }}
  ],
  "confidence": "Medium",
  "research_notes": "Limitations and unresolved questions"
}}

Allowed values:

credential_access:
Self-serve free, Self-serve paid, Admin approval,
Partnership/contact sales, Controlled / plan-dependent, Unknown

mcp_available:
Yes, No, Unknown

buildability:
Easy, Medium, Difficult, Not Buildable, Unknown

confidence:
High, Medium, Low

Rules:
1. Use only claims supported by the retrieved evidence.
2. Include actual URLs from the evidence.
3. Prefer official Salesforce documentation.
4. Do not claim MCP is unavailable merely because a result is missing.
5. Explain administrator and licensing requirements when supported.
6. If evidence is insufficient, use Unknown.
7. Return JSON only. No Markdown fences.
"""

    print("\nSending evidence to Gemini...")

    chat = client.chats.create(
        model=os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite"),
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.2
        )
    )

    response = chat.send_message(prompt)

    if not response.text:
        raise ValueError("Gemini returned an empty response")

    research_data = json.loads(response.text)

    print("\nValidating research with Pydantic...")

    result, output_path = validate_and_save(research_data, app)

    print("\n========== VALIDATED RESEARCH ==========")
    print(json.dumps(
        result.model_dump(),
        indent=4,
        ensure_ascii=False
    ))

    print("\nSUCCESS:", output_path)
    print("Confidence:", result.confidence)


if __name__ == "__main__":
    main()
