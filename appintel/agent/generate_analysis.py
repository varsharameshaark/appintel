import json
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RESEARCH_DIR = ROOT / "data" / "research"
REFINED_DIR = ROOT / "data" / "refined"
OUTPUT_DIR = ROOT / "data"


def load_records():
    records_by_id = {}

    for path in sorted(RESEARCH_DIR.glob("*.json")):
        with path.open("r", encoding="utf-8") as file:
            record = json.load(file)
            records_by_id[record["app_id"]] = record

    for path in sorted(REFINED_DIR.glob("*.json")):
        with path.open("r", encoding="utf-8") as file:
            record = json.load(file)
            records_by_id[record["app_id"]] = record

    return [records_by_id[key] for key in sorted(records_by_id)]


def flatten_list(values):
    return [str(value).strip() for value in values if str(value).strip()] if isinstance(values, list) else ([] if not values else [str(values)])


def main():
    records = load_records()
    if not records:
        raise SystemExit("No research records found.")

    df = pd.DataFrame(records)
    df.to_csv(OUTPUT_DIR / "appintel_research.csv", index=False)

    auth = Counter()
    access = Counter()
    buildability = Counter()
    mcp = Counter()
    api_types = Counter()
    category_access = defaultdict(Counter)

    for row in records:
        for value in flatten_list(row.get("auth_methods", [])):
            auth[value] += 1
        access[str(row.get("credential_access", "Unknown"))] += 1
        buildability[str(row.get("buildability", "Unknown"))] += 1
        mcp[str(row.get("mcp_available", "Unknown"))] += 1
        for value in flatten_list(row.get("api_type", [])):
            api_types[value] += 1
        category_access[str(row.get("category", "Unknown"))][str(row.get("credential_access", "Unknown"))] += 1

    category_data = {}
    for category, counters in sorted(category_access.items()):
        category_data[category] = dict(counters)

    analysis = {
        "applications_analyzed": len(records),
        "categories_analyzed": int(df["category"].nunique()) if "category" in df else len(category_data),
        "authentication_distribution": dict(auth.most_common()),
        "credential_access_distribution": dict(access.most_common()),
        "buildability_distribution": dict(buildability.most_common()),
        "mcp_distribution": dict(mcp.most_common()),
        "api_type_distribution": dict(api_types.most_common()),
        "credential_access_by_category": category_data,
        "data_source": "Refined data" if REFINED_DIR.glob("*.json") else "Baseline research data",
    }

    with (OUTPUT_DIR / "analysis.json").open("w", encoding="utf-8") as file:
        json.dump(analysis, file, indent=4, ensure_ascii=False)

    print(json.dumps(analysis, indent=2, ensure_ascii=False))
    print(f"CSV: {OUTPUT_DIR / 'appintel_research.csv'}")
    print(f"Analysis: {OUTPUT_DIR / 'analysis.json'}")


if __name__ == "__main__":
    main()
