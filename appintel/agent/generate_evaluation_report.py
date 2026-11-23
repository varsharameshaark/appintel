
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
VERIFICATION_DIR = BASE_DIR / "data" / "verification"

def generate_report():
    comparison_files = sorted(
        VERIFICATION_DIR.glob("*_comparison.json")
    )

    if not comparison_files:
        print("No comparison files found.")
        return

    total_apps = len(comparison_files)

    totals = {
        "matched_fields": 0,
        "partially_matched_fields": 0,
        "mismatched_fields": 0,
        "skipped_fields": 0,
        "manual_review_fields": 0,
        "evaluated_fields": 0
    }

    applications = []

    for file_path in comparison_files:
        with file_path.open("r", encoding="utf-8") as file:
            result = json.load(file)

        for metric in totals:
            totals[metric] += result.get(metric, 0)

        applications.append({
            "app_id": result["app_id"],
            "app_name": result["app_name"],
            "strict_agreement_percent":
                result["strict_agreement_percent"],
            "weighted_agreement_percent":
                result["weighted_agreement_percent"],
            "matched_fields": result["matched_fields"],
            "mismatched_fields": result["mismatched_fields"],
            "manual_review_fields": result["manual_review_fields"]
        })

    evaluated = totals["evaluated_fields"]

    strict_agreement = (
        totals["matched_fields"] / evaluated * 100
        if evaluated else 0
    )

    weighted_agreement = (
        (
            totals["matched_fields"]
            + 0.5 * totals["partially_matched_fields"]
        ) / evaluated * 100
        if evaluated else 0
    )

    report = {
        "total_applications_compared": total_apps,
        **totals,
        "overall_strict_agreement_percent": round(
            strict_agreement, 2
        ),
        "overall_weighted_agreement_percent": round(
            weighted_agreement, 2
        ),
        "applications": applications,
        "limitations": [
            "Only applications with comparison files are included.",
            "Agreement measures consistency with manually entered verification values, not absolute factual accuracy.",
            "Descriptive fields require human review.",
            "Analyst-assessed fields are not independent factual confirmations."
        ]
    }

    output_path = VERIFICATION_DIR / "overall_evaluation.json"

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(report, file, indent=4, ensure_ascii=False)

    print("\n" + "=" * 55)
    print("OVERALL EVALUATION REPORT")
    print("=" * 55)
    print(f"Applications compared: {total_apps}")
    print(f"Matched fields: {totals['matched_fields']}")
    print(f"Partially matched fields: {totals['partially_matched_fields']}")
    print(f"Mismatched fields: {totals['mismatched_fields']}")
    print(f"Skipped fields: {totals['skipped_fields']}")
    print(f"Fields requiring manual review: {totals['manual_review_fields']}")
    print(f"Overall strict agreement: {strict_agreement:.2f}%")
    print(f"Overall weighted agreement: {weighted_agreement:.2f}%")
    print(f"\nReport saved to: {output_path}")


if __name__ == "__main__":
    generate_report()
