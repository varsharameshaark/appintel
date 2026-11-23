import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
RESEARCH_DIR = DATA_DIR / "research"
REFINED_DIR = DATA_DIR / "refined"
VERIFY_DIR = DATA_DIR / "verification"
OUTPUT = ROOT / "index.html"


def load_json(path):
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def load_records():
    records_by_id = {}

    for path in sorted(RESEARCH_DIR.glob("*.json")):
        record = load_json(path)
        records_by_id[record["app_id"]] = record

    for path in sorted(REFINED_DIR.glob("*.json")):
        record = load_json(path)
        records_by_id[record["app_id"]] = record

    return [records_by_id[key] for key in sorted(records_by_id)]


def load_verification():
    path = VERIFY_DIR / "overall_evaluation.json"
    if path.exists():
        return load_json(path)
    return None


def escape(value):
    import html
    return html.escape("" if value is None else str(value), quote=True)


def main():
    records = load_records()
    analysis_path = DATA_DIR / "analysis.json"
    analysis = load_json(analysis_path) if analysis_path.exists() else {}
    evaluation = load_verification()

    rows = []
    for item in records:
        evidence_count = len(item.get("evidence", []))
        evidence_links = " ".join(
            f'<a href="{escape(e.get("url", ""))}" target="_blank" rel="noopener">Source</a>'
            for e in item.get("evidence", []) if e.get("url")
        )
        rows.append("""
<tr>
<td>{app_id}</td><td><strong>{app_name}</strong></td><td>{category}</td>
<td>{description}</td><td>{auth}</td><td>{access}</td>
<td>{api_type}</td><td>{mcp}</td><td>{buildability}</td>
<td>{blocker}</td><td>{confidence}</td><td>{evidence_count}<br>{links}</td>
</tr>""".format(
            app_id=escape(item.get("app_id")), app_name=escape(item.get("app_name")),
            category=escape(item.get("category")), description=escape(item.get("description")),
            auth=escape(", ".join(item.get("auth_methods", []))),
            access=escape(item.get("credential_access")),
            api_type=escape(", ".join(item.get("api_type", []))),
            mcp=escape(item.get("mcp_available")), buildability=escape(item.get("buildability")),
            blocker=escape(item.get("blocker")), confidence=escape(item.get("confidence")),
            evidence_count=evidence_count, links=evidence_links
        ))

    auth = analysis.get("authentication_distribution", {})
    access = analysis.get("credential_access_distribution", {})
    verdict = analysis.get("buildability_distribution", {})
    category_count = len(set(r.get("category", "") for r in records))

    def bar_list(data):
        if not data:
            return '<p class="empty">No data available yet.</p>'
        maximum = max(data.values())
        return "".join(
            f'<div class="bar-row"><div class="bar-label"><span>{escape(name)}</span><b>{value}</b></div>'
            f'<div class="bar-track"><div class="bar-fill" style="width:{(value / maximum * 100):.1f}%"></div></div></div>'
            for name, value in sorted(data.items(), key=lambda pair: (-pair[1], pair[0]))
        )

    eval_cards = ""
    if evaluation:
        eval_cards = f'''
        <div class="metric"><span>Apps compared</span><strong>{escape(evaluation.get("total_applications_compared", 0))}</strong></div>
        <div class="metric"><span>Strict agreement</span><strong>{escape(evaluation.get("overall_strict_agreement_percent", 0))}%</strong></div>
        <div class="metric"><span>Weighted agreement</span><strong>{escape(evaluation.get("overall_weighted_agreement_percent", 0))}%</strong></div>
        <div class="metric"><span>Matched fields</span><strong>{escape(evaluation.get("matched_fields", 0))}</strong></div>
        '''

    html = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>AppIntel — SaaS API Integration Intelligence</title>
<style>
:root{{--ink:#18212f;--muted:#64748b;--line:#dbe3ec;--accent:#6957d6;--cyan:#39b9b1;--paper:#f7f9fc}}
*{{box-sizing:border-box}} body{{margin:0;font-family:Inter,Segoe UI,Arial,sans-serif;color:var(--ink);background:var(--paper)}}
header{{background:linear-gradient(120deg,#17162d,#40376f);color:white;padding:54px 7vw}}header p{{max-width:760px;color:#d6d4e7}}
nav{{position:sticky;top:0;background:white;border-bottom:1px solid var(--line);z-index:5}}nav div{{display:flex;gap:24px;padding:14px 7vw}}nav a{{color:var(--ink);text-decoration:none;font-weight:700}}
main{{max-width:1250px;margin:auto;padding:36px 24px}}section{{margin-bottom:48px}}
.metrics{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:16px}}.metric{{background:white;border:1px solid var(--line);border-radius:14px;padding:20px}}.metric span{{display:block;color:var(--muted)}}.metric strong{{display:block;font-size:32px;margin-top:8px;color:var(--accent)}}
.grid{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:18px}}.card{{background:white;border:1px solid var(--line);border-radius:14px;padding:20px}}.card h3{{margin-top:0}}
.bar-row{{margin:10px 0}}.bar-label{{display:flex;justify-content:space-between;font-size:14px;margin-bottom:5px}}.bar-track{{height:8px;background:#edf1f6;border-radius:99px;overflow:hidden}}.bar-fill{{height:100%;background:linear-gradient(90deg,var(--accent),var(--cyan))}}
.toolbar{{display:flex;gap:12px;margin:16px 0}}input,select{{border:1px solid var(--line);border-radius:8px;padding:11px 12px;background:white}}input{{flex:1}}
.table-wrap{{overflow:auto;border:1px solid var(--line);border-radius:12px;background:white}}table{{border-collapse:collapse;width:100%;min-width:1500px}}th,td{{border-bottom:1px solid var(--line);padding:12px;text-align:left;vertical-align:top}}th{{background:#f1f4f8;position:sticky;top:0}}td{{font-size:13px}}
.empty{{color:var(--muted)}}.method{{background:white;border:1px solid var(--line);border-radius:14px;padding:22px}}footer{{text-align:center;color:var(--muted);padding:30px}}
@media(max-width:900px){{.metrics,.grid{{grid-template-columns:1fr 1fr}}}}@media(max-width:600px){{.metrics,.grid{{grid-template-columns:1fr}}header{{padding:36px 24px}}nav div{{padding:12px 24px}}}}
</style></head><body>
<header><h1>AppIntel</h1><h2>AI-Powered SaaS API Research & Integration Intelligence</h2><p>An evidence-driven view of API access, authentication, MCP availability and buildability across the Composio application research set.</p></header>
<nav><div><a href="#overview">Overview</a><a href="#patterns">Patterns</a><a href="#matrix">Research matrix</a><a href="#verification">Verification</a><a href="#method">Method</a></div></nav>
<main>
<section id="overview"><h2>Research overview</h2><div class="metrics">
<div class="metric"><span>Applications</span><strong>{len(records)}</strong></div>
<div class="metric"><span>Applications assessed</span><strong>{len(records)}</strong></div>
<div class="metric"><span>Categories</span><strong>{category_count}</strong></div>
<div class="metric"><span>Evidence sources</span><strong>{sum(len(r.get("evidence", [])) for r in records)}</strong></div>
</div></section>
<section id="patterns"><h2>Pattern analysis</h2><div class="grid">
<div class="card"><h3>Authentication</h3>{bar_list(auth)}</div>
<div class="card"><h3>Credential access</h3>{bar_list(access)}</div>
<div class="card"><h3>Buildability verdict</h3>{bar_list(verdict)}</div>
</div></section>
<section id="matrix"><h2>Research matrix</h2><div class="toolbar"><input id="search" placeholder="Search app, category, authentication, verdict..."><select id="category"><option value="">All categories</option></select><select id="buildability"><option value="">All buildability verdicts</option></select></div>
<div class="table-wrap"><table><thead><tr><th>ID</th><th>Application</th><th>Category</th><th>Description</th><th>Authentication</th><th>Credential access</th><th>API type</th><th>MCP</th><th>Buildability</th><th>Blocker</th><th>Confidence</th><th>Evidence</th></tr></thead><tbody id="rows">{''.join(rows)}</tbody></table></div></section>
<section id="verification"><h2>Verification results</h2><div class="metrics">{eval_cards or '<div class="metric"><span>Comparison data</span><strong>Pending</strong></div>'}</div></section>
<section id="method"><h2>Agent architecture & method</h2><div class="method"><ol><li><b>Dataset</b>: 100 applications with categories and starting URLs.</li><li><b>Discovery</b>: Composio focused official-documentation searches.</li><li><b>Evidence</b>: Raw responses are saved and reused; only actual URLs and crawled content are extracted.</li><li><b>Extraction</b>: Gemini produces structured Pydantic-validated JSON using evidence only.</li><li><b>Verification</b>: Field-level claims are checked against manual sources and refined.</li><li><b>Analysis</b>: CSV, JSON, charts and this HTML matrix are generated from the resulting dataset.</li></ol></div></section>
</main><footer>AppIntel • Evidence-first SaaS integration research</footer>
<script>
const search=document.querySelector('#search'),category=document.querySelector('#category'),buildability=document.querySelector('#buildability'),rows=[...document.querySelectorAll('#rows tr')];
const categories=[...new Set(rows.map(r=>r.children[2].textContent.trim()))].sort();const verdicts=[...new Set(rows.map(r=>r.children[8].textContent.trim()))].sort();
categories.forEach(v=>category.add(new Option(v,v))); verdicts.forEach(v=>buildability.add(new Option(v,v)));
function filter(){{const q=search.value.toLowerCase(),c=category.value,b=buildability.value;rows.forEach(r=>{{r.style.display=( (!q||r.textContent.toLowerCase().includes(q))&&(!c||r.children[2].textContent.trim()==c)&&(!b||r.children[8].textContent.trim()==b))?'':'none';}})}}
search.addEventListener('input',filter);category.addEventListener('change',filter);buildability.addEventListener('change',filter);
</script></body></html>'''

    OUTPUT.write_text(html, encoding="utf-8")
    print(f"Case study saved: {OUTPUT}")


if __name__ == "__main__":
    main()
