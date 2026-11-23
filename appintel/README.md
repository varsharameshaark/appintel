# AppIntel — AI-Powered SaaS API Research

AppIntel automates evidence-based research across 100 SaaS applications. It combines Composio web search/crawl, Gemini structured extraction, Pydantic validation, manual verification, refinement, and an HTML case study.

## Deliverables

- `index.html` — searchable/filterable case study
- `data/appintel_research.csv` — flattened research dataset
- `data/analysis.json` — aggregate pattern analysis
- `data/research/` — one validated JSON file per researched app
- `data/evidence/` — reusable raw Composio evidence
- `data/verification/` — baseline, refinement, and accuracy reports
- `agent/` — research, verification, analysis, and report scripts

## Setup

```powershell
python -m venv .venv
& .\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Add secrets to `.env`:

```text
COMPOSIO_API_KEY=your_composio_key
GEMINI_API_KEY=your_google_key
GEMINI_MODEL=gemini-3.5-flash-lite
```

Never commit `.env`.

## Commands

Validate the 100-app dataset:

```powershell
& .\.venv\Scripts\python.exe agent/load_dataset.py
```

Run the full research batch:

```powershell
& .\.venv\Scripts\python.exe agent/research_all_apps.py
```

The batch searches official documentation only through focused Composio searches, saves evidence, reuses existing evidence, and falls back across a bounded list of Gemini models. It also retries transient HTTP 503 responses.

Generate CSV and pattern analysis:

```powershell
& .\.venv\Scripts\python.exe agent/generate_analysis.py
```

Run verification and refinement:

```powershell
& .\.venv\Scripts\python.exe agent/compare_research.py
& .\.venv\Scripts\python.exe agent/generate_evaluation_report.py
& .\.venv\Scripts\python.exe agent/generate_refinement_report.py
& .\.venv\Scripts\python.exe agent/compare_refined_research.py
& .\.venv\Scripts\python.exe agent/generate_refinement_evaluation.py
```

Generate the searchable webpage:

```powershell
& .\.venv\Scripts\python.exe agent/generate_html_case_study.py
```

Open `index.html` directly or serve the repository locally:

```powershell
python -m http.server 8000
```

Visit `http://localhost:8000`.

## Research fields

Each application includes:

- Category and description
- Authentication methods
- Credential-access classification
- REST, GraphQL, MCP, and other API types
- API breadth
- MCP availability and evidence
- Buildability verdict and blocker
- Official or supporting evidence URLs
- Confidence and research notes

## Verification approach

Verification values are stored under `data/verification/`. The project distinguishes:

- Confirmed factual claims
- Analyst-assessed buildability and blockers
- Needs review fields
- AI-generated values without independent verification

Pattern counts must be interpreted using the number of completed research records, not as 100-app conclusions until the full batch completes.

## Model availability

Gemini availability varies by API key and account tier. The pipeline:

1. Uses `GEMINI_MODEL` when configured.
2. Tries bounded fallback models.
3. Retries HTTP 503 responses temporarily.
4. Records failures and resumes without losing saved evidence.

Do not rerun searches for applications that already have evidence or research JSON files.

## Current status

The dataset, Composio integration, evidence reuse, evidence extraction, Pydantic validation, verification scripts, analysis scripts, and HTML generator are implemented. Full 100-app completion depends on Gemini availability and per-app evidence quality.
