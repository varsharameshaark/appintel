
import json
from pathlib import Path


# Project directories
BASE_DIR = Path(__file__).resolve().parent.parent

REFINED_DIR = BASE_DIR / "data" / "refined"
VERIFICATION_DIR = BASE_DIR / "data" / "verification"
OUTPUT_DIR = VERIFICATION_DIR


# Fields suitable for direct comparison
COMPARABLE_FIELDS = [
    "auth_methods",
    "credential_access",
    "api_type",
    "mcp_available",
    "buildability"
]


def load_json(path):
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def normalize(value):
    """Normalize values before comparing them."""

    if isinstance(value, list):
        return sorted(
            str(item).strip().lower()
            for item in value
        )

    if value is None:
        return None

    return str(value).strip().lower()


def get_verified_value(item):
    """Support both verification JSON formats."""

    if not isinstance(item, dict):
        return None

    return item.get(
        "verified_value",
        item.get("value")
    )


def prepare_verified_fields(verification):
    """Support dictionary-based and list-based verification data."""

    raw_fields = verification.get("verified_fields", [])

    if isinstance(raw_fields, dict):
        return raw_fields

    if isinstance(raw_fields, list):
        verified_fields = {}

        for item in raw_fields:
            if isinstance(item, dict) and "field" in item:
                verified_fields[item["field"]] = item

        return verified_fields

    raise ValueError("Invalid verified_fields structure")


def compare_values(refined_value, verified_value):
    """Compare refined AI values with manually verified values."""

    refined_normalized = normalize(refined_value)
    verified_normalized = normalize(verified_value)

    if refined_normalized == verified_normalized:
        return "Matched"

    if (
        isinstance(refined_normalized, list)
        and isinstance(verified_normalized, list)
    ):
        if set(refined_normalized) & set(verified_normalized):
            return "Partially matched"

    return "Mismatch"


def compare_refined_research(app_id):

    # Find corresponding files
    verification_files = list(
        VERIFICATION_DIR.glob(
            f"{app_id:03d}_*_verification.json"
        )
    )

    refined_files = list(
        REFINED_DIR.glob(
            f"{app_id:03d}_*_refined.json"
        )
    )

    if not verification_files:
        raise FileNotFoundError(
            f"No verification file found for application {app_id}"
        )

    if not refined_files:
        raise FileNotFoundError(
            f"No refined research file found for application {app_id}"
        )

    if len(verification_files) > 1 or len(refined_files) > 1:
        raise ValueError(
            f"Multiple matching files found for application {app_id}"
        )

    verification = load_json(verification_files[0])
    refined = load_json(refined_files[0])

    print("\n" + "=" * 55)
    print("REFINED RESEARCH EVALUATION")
    print("=" * 55)

    print(f"Application: {refined['app_name']}")

    verified_fields = prepare_verified_fields(verification)

    results = []

    counts = {
        "Matched": 0,
        "Partially matched": 0,
        "Mismatch": 0,
        "Skipped": 0
    }

    # Compare each selected field
    for field in COMPARABLE_FIELDS:

        verification_item = verified_fields.get(field)

        if verification_item is None:
            counts["Skipped"] += 1

            results.append({
                "field": field,
                "status": "Skipped",
                "reason": "No manual verification available"
            })

            continue

        if not isinstance(verification_item, dict):
            counts["Skipped"] += 1

            results.append({
                "field": field,
                "status": "Skipped",
                "reason": "Invalid verification entry"
            })

            continue

        verification_status = verification_item.get(
            "status", ""
        )

        if verification_status == "Needs review":
            counts["Skipped"] += 1

            results.append({
                "field": field,
                "status": "Skipped",
                "reason": "Manual verification is incomplete"
            })

            continue

        verified_value = get_verified_value(
            verification_item
        )

        if verified_value is None:
            counts["Skipped"] += 1

            results.append({
                "field": field,
                "status": "Skipped",
                "reason": "Verified value is missing"
            })

            continue

        refined_value = refined.get(field)

        # Compare values
        status = compare_values(
            refined_value,
            verified_value
        )

        counts[status] += 1

        results.append({
            "field": field,
            "refined_value": refined_value,
            "verified_value": verified_value,
            "status": status
        })

        print(f"\nField: {field}")
        print(f"Refined value: {refined_value}")
        print(f"Verified value: {verified_value}")
        print(f"Result: {status}")

    # Calculate agreement
    evaluated = (
        counts["Matched"]
        + counts["Partially matched"]
        + counts["Mismatch"]
    )

    strict_agreement = (
        counts["Matched"] / evaluated * 100
        if evaluated > 0 else 0
    )

    weighted_agreement = (
        (
            counts["Matched"]
            + 0.5 * counts["Partially matched"]
        ) / evaluated * 100
        if evaluated > 0 else 0
    )

    # Prepare report
    report = {
        "app_id": app_id,
        "app_name": refined["app_name"],
        "evaluation_type": (
            "Refined research vs manual verification"
        ),
        "summary": {
            **counts,
            "evaluated_fields": evaluated,
            "strict_agreement_percent": round(
                strict_agreement, 2
            ),
            "weighted_agreement_percent": round(
                weighted_agreement, 2
            )
        },
        "field_results": results
    }

    # Save report
    output_path = (
        OUTPUT_DIR
        / f"{app_id:03d}_refined_comparison.json"
    )

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(
            report,
            file,
            indent=4,
            ensure_ascii=False
        )

    # Display summary
    print("\n" + "-" * 55)
    print("EVALUATION SUMMARY")
    print("-" * 55)

    print(f"Matched: {counts['Matched']}")
    print(f"Partially matched: {counts['Partially matched']}")
    print(f"Mismatched: {counts['Mismatch']}")
    print(f"Skipped: {counts['Skipped']}")
    print(f"Evaluated fields: {evaluated}")

    print(f"Strict agreement: {strict_agreement:.2f}%")
    print(f"Weighted agreement: {weighted_agreement:.2f}%")

    print(f"\nReport saved: {output_path}")

    return report


def main():

    verification_files = sorted(
        VERIFICATION_DIR.glob("*_verification.json")
    )

    successful = 0
    failed = 0

    for verification_file in verification_files:

        try:
            verification = load_json(verification_file)

            app_id = verification["app_id"]

            compare_refined_research(app_id)

            successful += 1

        except Exception as error:

            failed += 1

            print(
                f"\nERROR: {verification_file.name}: {error}"
            )

    print("\n" + "=" * 55)
    print("BATCH EVALUATION SUMMARY")
    print("=" * 55)

    print(f"Verification files found: {len(verification_files)}")
    print(f"Successfully evaluated: {successful}")
    print(f"Failed: {failed}")


if __name__ == "__main__":
    main()
