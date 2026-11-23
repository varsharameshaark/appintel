
import json
import re
from pathlib import Path


# Project directories
BASE_DIR = Path(__file__).resolve().parent.parent

RESEARCH_DIR = BASE_DIR / "data" / "research"
VERIFICATION_DIR = BASE_DIR / "data" / "verification"


# Fields suitable for direct comparison
COMPARABLE_FIELDS = [
    "auth_methods",
    "credential_access",
    "api_type",
    "mcp_available",
    "buildability"
]

# Descriptive fields require human review
MANUAL_REVIEW_FIELDS = [
    "description",
    "api_breadth",
    "mcp_evidence",
    "blocker"
]


def load_json(path):
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def normalize(value):
    """Normalize text before comparison."""

    if value is None:
        return ""

    return re.sub(
        r"\s+",
        " ",
        str(value).strip().lower()
    )


def find_research_file(app_id):
    """Find the AI research file using its application ID."""

    files = list(
        RESEARCH_DIR.glob(f"{app_id:03d}_*.json")
    )

    if not files:
        raise FileNotFoundError(
            f"No research file found for application ID {app_id}"
        )

    return files[0]


def find_verification_file(app_id, app_name):
    """Find the manual verification file using ID and app name."""

    slug = re.sub(
        r"[^a-z0-9]+",
        "_",
        app_name.lower()
    ).strip("_")

    verification_path = (
        VERIFICATION_DIR /
        f"{app_id:03d}_{slug}_verification.json"
    )

    if not verification_path.exists():
        raise FileNotFoundError(
            f"Verification file not found: {verification_path}"
        )

    return verification_path


def compare_values(ai_value, verified_value):
    """
    Compare structured values.

    Lists are compared using normalized set overlap.
    Scalar values are compared using normalized equality.
    """

    if isinstance(verified_value, list):

        if not isinstance(ai_value, list):
            return "Mismatch"

        ai_items = {
            normalize(item) for item in ai_value
        }

        verified_items = {
            normalize(item) for item in verified_value
        }

        if ai_items == verified_items:
            return "Matched"

        if ai_items.intersection(verified_items):
            return "Partially matched"

        return "Mismatch"

    if normalize(ai_value) == normalize(verified_value):
        return "Matched"

    return "Mismatch"


def compare_research(app_id):

    # Load AI research
    research_path = find_research_file(app_id)
    research = load_json(research_path)

    # Load corresponding manual verification
    verification_path = find_verification_file(
        app_id,
        research["app_name"]
    )

    verification = load_json(verification_path)

    verified_fields = verification.get(
        "verified_fields", {}
    )

    matched = 0
    partial = 0
    mismatched = 0
    skipped = 0
    manual_review = 0

    field_results = []

    print(
        f"\nResearch comparison: {research['app_name']}"
    )
    print("=" * 60)

    # Compare structured fields
    for field in COMPARABLE_FIELDS:

        verification_item = verified_fields.get(field)

        if not verification_item:
            skipped += 1
            continue

        verification_status = verification_item.get(
            "status", ""
        )

        # Only independently confirmed or analyst-assessed
        # fields are included in the comparison.
        if verification_status not in [
            "Confirmed",
            "Analyst-assessed"
        ]:
            skipped += 1
            continue

        # Support both old and new verification formats.
        verified_value = verification_item.get(
            "value",
            verification_item.get("verified_value")
        )

        if verified_value is None:
            skipped += 1
            continue

        ai_value = research.get(field)

        result = compare_values(
            ai_value,
            verified_value
        )

        if result == "Matched":
            matched += 1

        elif result == "Partially matched":
            partial += 1

        else:
            mismatched += 1

        field_results.append({
            "field": field,
            "ai_value": ai_value,
            "verified_value": verified_value,
            "verification_status": verification_status,
            "comparison_result": result
        })

        print(f"\nField: {field}")
        print(f"AI value: {ai_value}")
        print(f"Verified value: {verified_value}")
        print(f"Result: {result}")

    # Descriptive fields are not automatically scored.
    for field in MANUAL_REVIEW_FIELDS:

        if field in verified_fields:
            status = verified_fields[field].get(
                "status", ""
            )

            if status in [
                "Confirmed",
                "Analyst-assessed"
            ]:
                manual_review += 1

    evaluated = matched + partial + mismatched

    if evaluated > 0:

        strict_coverage = (
            matched / evaluated
        ) * 100

        weighted_coverage = (
            matched + 0.5 * partial
        ) / evaluated * 100

    else:
        strict_coverage = 0
        weighted_coverage = 0

    # Display summary
    print("\n" + "=" * 60)
    print("EVALUATION SUMMARY")
    print("=" * 60)

    print(f"Matched fields: {matched}")
    print(f"Partially matched fields: {partial}")
    print(f"Mismatched fields: {mismatched}")
    print(f"Skipped fields: {skipped}")
    print(f"Fields requiring manual review: {manual_review}")
    print(f"Evaluated fields: {evaluated}")

    print(f"Strict agreement: {strict_coverage:.1f}%")
    print(f"Weighted agreement: {weighted_coverage:.1f}%")

    # Save comparison report
    output = {
        "app_id": app_id,
        "app_name": research["app_name"],
        "matched_fields": matched,
        "partially_matched_fields": partial,
        "mismatched_fields": mismatched,
        "skipped_fields": skipped,
        "manual_review_fields": manual_review,
        "evaluated_fields": evaluated,
        "strict_agreement_percent": round(
            strict_coverage, 2
        ),
        "weighted_agreement_percent": round(
            weighted_coverage, 2
        ),
        "evaluation_method": (
            "Structured field comparison against manually "
            "verified values. Supports both value and "
            "verified_value verification formats. "
            "Descriptive fields require human review."
        ),
        "field_results": field_results
    }

    output_path = (
        VERIFICATION_DIR /
        f"{app_id:03d}_comparison.json"
    )

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(
            output,
            file,
            indent=4,
            ensure_ascii=False
        )

    print(f"\nComparison saved to: {output_path}")


if __name__ == "__main__":

    research_files = sorted(
        RESEARCH_DIR.glob("*.json")
    )

    if not research_files:
        print("No research files found.")
        raise SystemExit(0)

    successful = 0
    failed = 0

    for research_path in research_files:

        try:
            research = load_json(research_path)
            app_id = research["app_id"]

            compare_research(app_id)
            successful += 1

        except Exception as error:
            print(
                f"\nCould not compare "
                f"{research_path.name}: {error}"
            )
            failed += 1

    print("\n" + "=" * 60)
    print("BATCH COMPARISON SUMMARY")
    print("=" * 60)

    print(f"Research files found: {len(research_files)}")
    print(f"Successfully compared: {successful}")
    print(f"Skipped / failed: {failed}")
