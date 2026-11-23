
from models import AppResearch

sample_data = {
    "app_id": 1,
    "app_name": "Salesforce",
    "category": "CRM and Sales",
    "description": "Enterprise CRM platform.",
    "auth_methods": ["OAuth 2.0"],
    "credential_access": "Controlled / plan-dependent",
    "api_type": ["REST", "SOAP", "GraphQL"],
    "api_breadth": "Extensive enterprise APIs.",
    "mcp_available": "Yes",
    "mcp_evidence": "Official Hosted MCP Servers.",
    "buildability": "Medium",
    "blocker": "Complex permissions and OAuth configuration.",
    "evidence": [],
    "confidence": "Medium",
    "research_notes": "Some details require further verification."
}

try:
    result = AppResearch.model_validate(sample_data)

    print("Model validation successful!")
    print(result.model_dump_json(indent=4))

except Exception as exc:
    print("Model validation failed:")
    print(exc)
