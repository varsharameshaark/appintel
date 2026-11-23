import json
import os
import time
from pathlib import Path
from urllib.parse import urlparse
import random

from dotenv import load_dotenv
from composio import Composio
from composio_gemini import GeminiProvider
from google import genai
from google.genai import types

from load_dataset import load_apps
from research_engine import validate_and_save


# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

EVIDENCE_DIR = ROOT / "data" / "evidence"
PROGRESS_PATH = ROOT / "data" / "batch_progress.json"

EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

# Phase 2: full 100-app batch. SKIP_EXISTING and saved evidence prevent duplicate work.
TEST_APP_ID = None
MAX_APPS = None

SKIP_EXISTING = True

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
COMPOSIO_USER_ID = "appintel-local-test"
COMPOSIO_SESSION_ID = "page"


# --------------------------------------------------
# FILE UTILITIES
# --------------------------------------------------

def save_json(path, data):
    """Save JSON safely using a temporary file."""

    path.parent.mkdir(parents=True, exist_ok=True)

    temporary_path = path.with_suffix(path.suffix + ".tmp")

    with temporary_path.open("w", encoding="utf-8") as file:
        json.dump(
            data,
            file,
            indent=4,
            ensure_ascii=False,
            default=str
        )

    temporary_path.replace(path)


def load_progress():
    """Load previous batch progress or create a new record."""

    if PROGRESS_PATH.exists():
        with PROGRESS_PATH.open("r", encoding="utf-8") as file:
            progress = json.load(file)
    else:
        progress = {
            "completed": [],
            "failed": {},
            "skipped": [],
            "last_updated": None
        }

    progress.setdefault("completed", [])
    progress.setdefault("failed", {})
    progress.setdefault("skipped", [])

    return progress


def update_progress(progress):
    progress["last_updated"] = time.strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    save_json(PROGRESS_PATH, progress)


def make_slug(name):
    return name.lower().replace(" ", "_").replace("/", "_")


# --------------------------------------------------
# SEARCH QUERY GENERATION
# --------------------------------------------------

def get_domain(app):
    parsed = urlparse(app["starting_url"])

    domain = parsed.netloc.lower()

    if domain.startswith("www."):
        domain = domain[4:]

    return domain


def build_search_requests(app):
    """
    Create two focused searches per application.

    Search 1: Authentication and API documentation.
    Search 2: MCP and integration documentation.
    """

    name = app["name"]
    domain = get_domain(app)

    return [
        {
            "query": (
                f'"{name}" official developer documentation '
                f"API authentication OAuth API key REST GraphQL"
            ),
            "search_service": "google",
            "max_results": 5,
            "crawl_results": 2,
            "include_sites": [domain]
        },
        {
            "query": (
                f'"{name}" official developer documentation '
                f"MCP Model Context Protocol integrations API"
            ),
            "search_service": "google",
            "max_results": 3,
            "crawl_results": 1,
            "include_sites": [domain]
        }
    ]


# --------------------------------------------------
# COMPOSIO INITIALIZATION
# --------------------------------------------------

def initialize_composio():
    print("\nInitializing Composio...")

    composio = Composio(
        provider=GeminiProvider()
    )

    session = composio.create(
        user_id=COMPOSIO_USER_ID
    )

    available_tools = session.tools()

    execute_tool = next(
        (
            tool for tool in available_tools
            if tool.__name__ == "COMPOSIO_MULTI_EXECUTE_TOOL"
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

    workbench = next(
        (
            tool for tool in available_tools
            if tool.__name__ == "COMPOSIO_REMOTE_WORKBENCH"
        ),
        None
    )

    if execute_tool is None:
        raise RuntimeError(
            "COMPOSIO_MULTI_EXECUTE_TOOL was not found."
        )

    if bash_tool is None and workbench is None:
        print("Warning: no remote response-processing tools available.")

    print(
        f"Composio initialized. "
        f"{len(available_tools)} tools available."
    )

    return execute_tool, bash_tool, workbench


# --------------------------------------------------
# SEARCH EXECUTION
# --------------------------------------------------

def execute_search(execute_tool, app):

    print(
        f"Searching official documentation for {app['name']}..."
    )

    result = execute_tool(
        tools=[
            {
                "tool_slug": "SEARCH1API_SEARCH_WEB",
                "arguments": {
                    "requests": build_search_requests(app)
                }
            }
        ],
        thought=(
            f"Research {app['name']} using official documentation. "
            "Find evidence about authentication, API capabilities, "
            "credential access, and MCP availability."
        ),
        sync_response_to_workbench=True,
        current_step=f"Searching {app['name']} documentation",
        current_step_metric="1 of 2",
        session_id=COMPOSIO_SESSION_ID
    )

    # Convert SDK objects into JSON-compatible data if necessary.
    if hasattr(result, "model_dump"):
        result = result.model_dump()

    if not isinstance(result, dict):
        raise ValueError(
            "Composio returned an unexpected response format."
        )

    return result


# --------------------------------------------------
# EVIDENCE EXTRACTION
# --------------------------------------------------

def extract_evidence(execution_data):

    evidence_items = []

    def walk(value):
        if isinstance(value, dict):
            url = value.get("link") or value.get("url") or ""
            if isinstance(url, str) and url.startswith(("https://", "http://")):
                evidence_items.append({
                    "title": value.get("title") or value.get("metadata", {}).get("title", "") if isinstance(value, dict) else "",
                    "url": url,
                    "snippet": value.get("snippet") or value.get("description") or "",
                    "content": value.get("content") or "",
                    "research_method": "Crawl" if value.get("content") else "Search",
                })
            for nested in value.values():
                walk(nested)
        elif isinstance(value, list):
            for nested in value:
                walk(nested)

    # Prefer complete inline data, but safely inspect nested variants.
    for execution in execution_data.get("results", []):
        response = execution.get("response", {})
        if not response.get("successful"):
            continue
        if isinstance(response.get("data"), dict):
            walk(response["data"])

    # Also handle SDK/model forms where data may be nested differently.
    walk(execution_data)

    unique_items = []
    seen_urls = set()
    for item in evidence_items:
        if item["url"] not in seen_urls:
            seen_urls.add(item["url"])
            unique_items.append(item)

    return unique_items


def extract_from_remote_response(execution_data, bash_tool, app):
    remote_info = execution_data.get("remote_file_info", {})
    remote_path = remote_info.get("file_path")

    if not remote_path or bash_tool is None:
        return execution_data

    slug = make_slug(app["name"])

    code = (
        "python3 -c "
        + repr(
            "import json\n"
            f"source={remote_path!r}\n"
            "out=[]\n"
            "data=json.load(open(source, 'r', encoding='utf-8'))\n"
            "def walk(v):\n"
            "    if isinstance(v, dict):\n"
            "        u=v.get('link') or v.get('url') or ''\n"
            "        if isinstance(u,str) and u.startswith(('https://','http://')):\n"
            "            out.append({'title':v.get('title',''),'url':u,'snippet':v.get('snippet',''),'content':v.get('content') or ''})\n"
            "        for x in v.values(): walk(x)\n"
            "    elif isinstance(v,list):\n"
            "        for x in v: walk(x)\n"
            "walk(data)\n"
            f"open('/mnt/files/{slug}_evidence.json','w',encoding='utf-8').write(json.dumps(out,ensure_ascii=False))\n"
            "print(json.dumps(out,ensure_ascii=False))\n"
        )
    )

    try:
        remote_result = bash_tool(
            command=code,
            session_id=COMPOSIO_SESSION_ID
        )
    except Exception as error:
        print(f"Remote evidence extraction failed: {error}")
        return execution_data

    extracted = []

    def find_json(value):
        nonlocal extracted
        if isinstance(value, dict):
            for nested in value.values():
                find_json(nested)
        elif isinstance(value, list):
            for nested in value:
                find_json(nested)
        elif isinstance(value, str):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    extracted = parsed
            except Exception:
                pass

    find_json(remote_result)

    if extracted:
        execution_data["remote_extracted_evidence"] = extracted
        print(f"Remote evidence extraction found {len(extracted)} URLs.")
    else:
        print("Remote evidence extraction returned no parseable evidence.")

    return execution_data


# --------------------------------------------------
# GEMINI RESEARCH PROMPT
# --------------------------------------------------

def build_gemini_prompt(app, evidence_items):

    return f"""
You are AppIntel, an SaaS API research analyst.

Research the application using ONLY the supplied evidence.

APPLICATION:
{json.dumps(app, indent=2, ensure_ascii=False)}

RETRIEVED EVIDENCE:
{json.dumps(evidence_items, indent=2, ensure_ascii=False)}

RESEARCH REQUIREMENTS:

1. One-line application description.
2. Authentication methods.
3. Credential access requirements.
4. API types such as REST, GraphQL, SOAP, or other.
5. API breadth and capabilities.
6. Official MCP availability.
7. Buildability.
8. Main implementation blockers.
9. Evidence sources.

IMPORTANT RULES:

- Prefer official documentation.
- Do not invent facts, URLs, excerpts, or sources.
- Only use URLs present in the supplied evidence.
- Distinguish search snippets from crawled page content.
- Do not claim a page was crawled if its content is empty.
- Do not claim MCP is unavailable merely because no result was found.
- Do not claim manual verification.
- Distinguish free developer access from production access.
- Explain plan, licensing, and administrator requirements when supported.
- Use Unknown when evidence is insufficient.
- Buildability is an analyst assessment, not an official vendor classification.
- Use Medium or Low confidence when important claims remain uncertain.

Allowed credential_access values:

"Self-serve free"
"Self-serve paid"
"Admin approval"
"Partnership/contact sales"
"Controlled / plan-dependent"
"Unknown"

Allowed mcp_available values:

"Yes"
"No"
"Unknown"

Allowed buildability values:

"Easy"
"Medium"
"Difficult"
"Not Buildable"
"Unknown"

Allowed confidence values:

"High"
"Medium"
"Low"

Return exactly one JSON object with these fields:

{{
    "app_id": {app["id"]},
    "app_name": "{app["name"]}",
    "category": "{app["category"]}",
    "description": "",
    "auth_methods": [],
    "credential_access": "Unknown",
    "api_type": [],
    "api_breadth": "",
    "mcp_available": "Unknown",
    "mcp_evidence": "",
    "buildability": "Unknown",
    "blocker": "",
    "evidence": [
        {{
            "url": "",
            "title": "",
            "source_type": "Official",
            "supports": "",
            "research_method": "Search",
            "excerpt": ""
        }}
    ],
    "confidence": "Low",
    "research_notes": ""
}}

For each evidence item:
- URL must exactly match a supplied evidence URL.
- Use "Crawl" only when actual page content was returned.
- Use "Search" when only a search result/snippet was returned.
- Use "Official" only when the source is the application's official documentation.
- Include a short relevant excerpt or faithful paraphrase.

Return JSON only. Do not use Markdown fences.
"""


# --------------------------------------------------
# GEMINI ANALYSIS
# --------------------------------------------------


def analyze_evidence(client, app, evidence_items):

    print("Sending retrieved evidence to Gemini...")

    prompt = build_gemini_prompt(app, evidence_items)

    fallback_models = [
        os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite"),
        "gemini-3.8-flash",
        "gemini-3.6-flash",
        "gemini-flash-latest",
    ]

    fallback_models = list(dict.fromkeys(fallback_models))

    last_error = None

    for model_name in fallback_models:

        for attempt in range(1, 4):

            try:
                print(
                    f"Sending evidence to Gemini "
                    f"({model_name}, attempt {attempt}/3)..."
                )

                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.2
                    )
                )

                break

            except Exception as error:
                last_error = error
                error_text = str(error)

                if any(code in error_text for code in ("503", "429", "UNAVAILABLE", "RESOURCE_EXHAUSTED")):
                    delay = random.uniform(2, 5) * (2 ** (attempt - 1))
                    print(
                        f"Model temporarily unavailable; "
                        f"retrying in {delay:.1f} seconds..."
                    )
                    time.sleep(delay)
                    continue

                if "404" in error_text or "NOT_FOUND" in error_text:
                    print(f"Model unavailable for this API key: {model_name}")
                    break

                raise

        else:
            continue

        if 'response' in locals() and response.text:
            break

    else:
        raise RuntimeError(
            f"No Gemini model responded successfully. Last error: {last_error}"
        )

    if not response.text:
        raise ValueError("Gemini returned an empty response.")

    research_data = json.loads(response.text)

    allowed_urls = {item["url"] for item in evidence_items}

    research_data["evidence"] = [
        item for item in research_data.get("evidence", [])
        if item.get("url") in allowed_urls
    ]

    if not research_data["evidence"]:
        raise ValueError(
            "Gemini did not return valid evidence URLs."
        )

    return research_data



# --------------------------------------------------
# PROCESS ONE APPLICATION
# --------------------------------------------------


def process_application(
    app,
    execute_tool,
    gemini_client,
    bash_tool=None,
    workbench=None,
):

    app_id = app["id"]
    slug = make_slug(app["name"])

    evidence_path = (
        EVIDENCE_DIR / f"{app_id:03d}_{slug}_evidence.json"
    )

    print("\n" + "=" * 60)
    print(f"APPLICATION: {app['name']} (ID: {app_id})")
    print("=" * 60)

    # 1. Reuse previously saved evidence.
    if evidence_path.exists():

        print("Existing raw evidence found.")
        print("Reusing:", evidence_path)

        with evidence_path.open("r", encoding="utf-8") as file:
            execution_data = json.load(file)

    else:

        # Search only if evidence does not exist.
        execution_data = execute_search(
            execute_tool,
            app
        )

        save_json(
            evidence_path,
            execution_data
        )

        print("Raw search response saved:", evidence_path)

    # 2. Extract usable evidence.
    execution_data = extract_from_remote_response(
        execution_data,
        bash_tool,
        app
    )

    evidence_items = extract_evidence(execution_data)

    if not evidence_items and execution_data.get("remote_extracted_evidence"):
        evidence_items = execution_data["remote_extracted_evidence"]

    if not evidence_items:
        raise ValueError(
            "No usable evidence returned by Composio."
        )

    print(
        f"Extracted {len(evidence_items)} unique evidence sources."
    )

    # 3. Analyze evidence using Gemini.
    research_data = analyze_evidence(
        gemini_client,
        app,
        evidence_items
    )

    # 4. Validate and save research.
    result, output_path = validate_and_save(
        research_data,
        app
    )

    print("\nSUCCESS:", result.app_name)
    print("Research saved:", output_path)
    print("Evidence saved:", evidence_path)
    print("Confidence:", result.confidence)

    return output_path



# --------------------------------------------------
# MAIN BATCH PIPELINE
# --------------------------------------------------

def main():

    if not os.getenv("COMPOSIO_API_KEY"):
        raise ValueError(
            "COMPOSIO_API_KEY is missing from .env"
        )

    if not os.getenv("GEMINI_API_KEY"):
        raise ValueError(
            "GEMINI_API_KEY is missing from .env"
        )

    print("\nInitializing AppIntel research pipeline...")

    apps = load_apps()

    # Select application for the initial test.
    if TEST_APP_ID is not None:
        apps = [
            app for app in apps
            if app["id"] == TEST_APP_ID
        ]

        if not apps:
            raise ValueError(
                f"Application ID {TEST_APP_ID} was not found."
            )

    progress = load_progress()

    # Initialize external services once.
    execute_tool, bash_tool, workbench = initialize_composio()
    gemini_client = genai.Client()

    # Apply maximum application limit.
    if MAX_APPS is not None:
        apps = apps[:MAX_APPS]

    print(f"\nApplications selected: {len(apps)}")

    successful = 0
    failed = 0
    skipped = 0

    for index, app in enumerate(apps, start=1):

        app_id = app["id"]
        slug = make_slug(app["name"])

        existing_research = (
            ROOT / "data" / "research"
            / f"{app_id:03d}_{slug}.json"
        )

        print(
            f"\nBatch progress: {index}/{len(apps)}"
        )

        # Resume support: do not repeat successful research.
        if SKIP_EXISTING and existing_research.exists():

            print(
                f"SKIPPED: Existing research found for {app['name']}."
            )

            if app_id not in progress["skipped"]:
                progress["skipped"].append(app_id)

            skipped += 1
            update_progress(progress)
            continue

        try:

            process_application(
                app,
                execute_tool,
                gemini_client,
                bash_tool,
                workbench,
            )

            if app_id not in progress["completed"]:
                progress["completed"].append(app_id)

            progress["failed"].pop(str(app_id), None)

            successful += 1

        except Exception as error:

            error_message = (
                f"{type(error).__name__}: {error}"
            )

            print(f"\nFAILED: {app['name']}")
            print(error_message)

            progress["failed"][str(app_id)] = {
                "app_name": app["name"],
                "error": error_message,
                "timestamp": time.strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
            }

            failed += 1

        finally:
            update_progress(progress)

        # Small delay between applications.
        time.sleep(2)

    # Final batch summary.
    print("\n" + "=" * 60)
    print("APPINTEL BATCH RESEARCH SUMMARY")
    print("=" * 60)

    print("Applications selected:", len(apps))
    print("Successful:", successful)
    print("Failed:", failed)
    print("Skipped:", skipped)

    print(
        "Total completed in progress file:",
        len(progress["completed"])
    )

    print(
        "Total failures in progress file:",
        len(progress["failed"])
    )

    print("Progress file:", PROGRESS_PATH)
    print("=" * 60)


# --------------------------------------------------
# ENTRY POINT
# --------------------------------------------------

if __name__ == "__main__":
    main()
