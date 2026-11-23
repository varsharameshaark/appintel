
import json
import re
from copy import deepcopy
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

VERIFICATION_DIR = BASE_DIR / "data" / "verification"
RESEARCH_DIR = BASE_DIR / "data" / "research"
REFINED_DIR = BASE_DIR / "data" / "refined"

REFINED_DIR.mkdir(parents=True, exist_ok=True)


def load_json(path):
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_json(path, data):
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)


def normalize_name(name):
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def find_research_file(app_id):
    files = list(RESEARCH_DIR.glob(f"{app_id:03d}_*.json"))

    if not files:
        raise FileNotFoundError(
            f"No research file found for application ID {app_id}"
        )

    return files[0]


def get_verified_value(item):
    """
    Support both verification formats:
    Salesforce: verified_value
    HubSpot: value
    """

    if "verified_value" in item:
        return item["verified_value"]

    return item.get("value")


def refine_research(app_id):

    research_path = find_research_file(app_id)
    research = load_json(research_path)

    verification_path = (
        VERIFICATION_DIR /
        f"{app_id:03d}_{normalize_name(research['app_name'])}_verification.json"
    )

    if not verification_path.exists():
        raise FileNotFoundError(
            f"Verification file not found: {verification_path}"
        )

    verification = load_json(verification_path)

    refined = deepcopy(research)

    changes = []
    unchanged = []
    skipped = []

    field_status = {}
    verified_fields = verification.get("verified_fields", {})

    for field, item in verified_fields.items():

        status = item.get("status", "Unknown")
        verified_value = get_verified_value(item)

        field_status[field] = status

        if status == "Needs review":
            skipped.append({
                "field": field,
                "reason": "Manual verification is incomplete"
            })
            continue

        if status not in ["Confirmed", "Analyst-assessed"]:
            skipped.append({
                "field": field,
                "reason": f"Unsupported verification status: {status}"
            })
            continue

        if verified_value is None:
            skipped.append({
                "field": field,
                "reason": "No verified value supplied"
            })
            continue

        original_value = research.get(field)

        if original_value != verified_value:

            refined[field] = verified_value

            changes.append({
                "field": field,
                "original_ai_value": original_value,
                "refined_value": verified_value,
                "change_type": (
                    "Evidence-verified correction"
                    if status == "Confirmed"
                    else "Analyst-assessed refinement"
                ),
                "verification_status": status
            })

        else:
            unchanged.append(field)

    # Mark research fields without manual verification.
    for field in research:
        if field not in field_status and field not in [
            "evidence",
            "research_notes",
            "confidence"
        ]:
            field_status[field] = "AI-generated / Not independently verified"

    # Add field-level verification metadata.
    refined["verification_status"] = field_status

    refined["research_notes"] = (
        research.get("research_notes", "")
        + " Refined using manually reviewed verification data. "
        + "See verification_status for field-level verification."
    )

    slug = normalize_name(research["app_name"])

    refined_path = (
        REFINED_DIR /
        f"{app_id:03d}_{slug}_refined.json"
    )

    save_json(refined_path, refined)

    report = {
        "app_id": app_id,
        "app_name": research["app_name"],
        "baseline_type": "Original AI research file",
        "fields_changed": len(changes),
        "fields_unchanged": len(unchanged),
        "fields_skipped": len(skipped),
        "changes": changes,
        "unchanged_fields": unchanged,
        "skipped_fields": skipped,
        "verification_status": field_status,
        "limitations": verification.get("limitations", []),
        "interpretation": (
            "Refined values are derived from manually reviewed verification data. "
            "Confirmed changes and analyst-assessed changes are distinguished. "
            "Unverified AI-generated fields are explicitly labelled. "
            "This process does not independently measure factual accuracy."
        )
    }

    report_path = (
        VERIFICATION_DIR /
        f"{app_id:03d}_refinement_report.json"
    )

    save_json(report_path, report)

    print("\n" + "=" * 55)
    print("RESEARCH REFINEMENT REPORT")
    print("=" * 55)
    print(f"Application: {research['app_name']}")
    print(f"Fields changed: {len(changes)}")
    print(f"Fields unchanged: {len(unchanged)}")
    print(f"Fields skipped: {len(skipped)}")

    for change in changes:
        print(f"\nField: {change['field']}")
        print(f"Original: {change['original_ai_value']}")
        print(f"Refined: {change['refined_value']}")
        print(f"Change type: {change['change_type']}")

    for item in skipped:
        print(f"\nSkipped: {item['field']}")
        print(f"Reason: {item['reason']}")

    print(f"\nRefined research saved: {refined_path}")
    print(f"Refinement report saved: {report_path}")


if __name__ == "__main__":

    verification_files = sorted(
        VERIFICATION_DIR.glob("*_verification.json")
    )

    successful = 0
    failed = 0

    for verification_path in verification_files:

        try:
            verification = load_json(verification_path)
            app_id = verification["app_id"]

            refine_research(app_id)
            successful += 1

        except Exception as error:
            print(
                f"\nCould not refine {verification_path.name}: {error}"
            )
            failed += 1

    print("\n" + "=" * 55)
    print("BATCH REFINEMENT SUMMARY")
    print("=" * 55)
    print(f"Verification files found: {len(verification_files)}")
    print(f"Successfully refined: {successful}")
    print(f"Failed: {failed}")
