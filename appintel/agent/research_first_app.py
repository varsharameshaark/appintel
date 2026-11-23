
import json

from models import AppResearch
from dotenv import load_dotenv
from composio import Composio
from composio_gemini import GeminiProvider
from google import genai
from google.genai import types

load_dotenv()

print("Initializing AppIntel research agent...")

composio = Composio(provider=GeminiProvider())
session = composio.create(user_id="appintel-local-test")
tools = session.tools()

print(f"Composio initialized. {len(tools)} tools available.")

client = genai.Client()

config = types.GenerateContentConfig(
    tools=tools
)

chat = client.chats.create(
    model="gemini-3.5-flash-lite",
    config=config
)

prompt = """
You are AppIntel, an SaaS API research agent.

Research Salesforce using Composio web search and URL crawling tools.

Application:
- ID: 1
- Name: Salesforce
- Category: CRM and Sales
- Website: https://www.salesforce.com/

Research:
1. Description
2. Authentication methods
3. Credential access requirements
4. API types
5. API breadth
6. Official MCP availability
7. Buildability
8. Main implementation blockers
9. Evidence sources

Rules:
- Prefer official Salesforce developer documentation.
- Never invent URLs, excerpts or research methods.
- Use third-party sources only when necessary.
- Distinguish free developer access from production API access.
- If free developer access exists but production depends on
  paid plans, licenses or admin permissions, use
  "Controlled / plan-dependent".
- Do not confuse OAuth2 flows with separate protocols.
- MCP availability must be Yes, No or Unknown.
- Verify official Hosted MCP separately from Salesforce DX MCP.
- Do not claim a page was crawled unless its contents were returned.
- Record the lifecycle status of MCP offerings.
- Use Unknown when evidence is insufficient.
- Use High confidence only when all important findings
  have sufficient official supporting evidence.
- Otherwise use Medium or Low.

Official MCP documentation to investigate:
https://developer.salesforce.com/docs/platform/hosted-mcp-servers/guide/hosted-mcp-servers-overview.html

https://developer.salesforce.com/docs/platform/hosted-mcp-servers/guide/servers-reference.html

credential_access must be exactly one of:
"Self-serve free", "Self-serve paid", "Admin approval",
"Partnership/contact sales", "Controlled / plan-dependent",
"Unknown".

buildability must be exactly one of:
"Easy", "Medium", "Difficult", "Not Buildable", "Unknown".

For each evidence source return:
- url
- title
- source_type: Official, Third-party, or Unverified
- supports
- research_method: Search, Crawl, or Manual verification
- excerpt

Return ONLY valid JSON with this structure:

{
  "app_id": 1,
  "app_name": "Salesforce",
  "category": "CRM and Sales",
  "description": "One-line description",
  "auth_methods": [],
  "credential_access": "Unknown",
  "api_type": [],
  "api_breadth": "Description",
  "mcp_available": "Unknown",
  "mcp_evidence": "Evidence or explanation",
  "buildability": "Unknown",
  "blocker": "Main implementation blocker",
  "evidence": [],
  "confidence": "Low",
  "research_notes": "Uncertainties and limitations"
}
"""

print("\nStarting Salesforce research...\n")

try:
    response = chat.send_message(prompt)

    print("\n========== APPINTEL RESEARCH RESULT ==========\n")

    raw_text = response.text

    if not raw_text:
        print("Gemini did not return a text response.")

        for candidate in response.candidates or []:
            for part in candidate.content.parts:
                if part.function_call:
                    print("Function called:", part.function_call.name)
                    print("Arguments:", part.function_call.args)

        raise ValueError(
            "No JSON text returned. A function call or empty response "
            "was received instead."
        )

    raw_result = raw_text.strip()

    # Remove Markdown code fences if Gemini adds them
    if raw_result.startswith("```"):
        raw_result = raw_result.split("\n", 1)[1]
        raw_result = raw_result.rsplit("```", 1)[0].strip()

    # Convert response into JSON
    research_data = json.loads(raw_result)

    # Validate using Pydantic
    app_result = AppResearch.model_validate(research_data)

    # Save result
    output_path = "data/salesforce_research.json"

    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(
            app_result.model_dump(),
            file,
            indent=4,
            ensure_ascii=False
        )

    print(app_result.model_dump_json(indent=4))
    print(f"\nResearch saved successfully: {output_path}")

except Exception as exc:
    print("\nResearch validation or saving failed.")
    print(f"{type(exc).__name__}: {exc}")

    print("\nRaw Gemini response:")
    print(response.text if "response" in locals() else "No response received.")
