
import json
from pathlib import Path


# Project directories
BASE_DIR = Path(__file__).resolve().parent.parent

VERIFICATION_DIR = BASE_DIR / "data" / "verification"
OUTPUT_DIR = VERIFICATION_DIR


def load_json(path):
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def get_application_ids():
    """Find applications with both original and refined reports."""

    original_files = VERIFICATION_DIR.glob("*_comparison.json")
    refined_files = VERIFICATION_DIR.glob("*_refined_comparison.json")

    original_ids = {
        int(path.name.split("_")[0])
        for path in original_files
        if path.name[:3].isdigit()
        and "_refined_comparison" not in path.name
    }

    refined_ids = {
        int(path.name.split("_")[0])
        for path in refined_files
        if path.name[:3].isdigit()
    }

    return sorted(original_ids & refined_ids)


def get_metric(report, metric_name):
    """Read a metric from either supported report structure."""

    if "summary" in report:
        return report["summary"].get(metric_name, 0)

    return report.get(metric_name, 0)


def calculate_improvement(original, refined):
    """Compare agreement before and after refinement."""

    original_strict = get_metric(
        original, "strict_agreement_percent"
    )

    refined_strict = get_metric(
        refined, "strict_agreement_percent"
    )

    original_weighted = get_metric(
        original, "weighted_agreement_percent"
    )

    refined_weighted = get_metric(
        refined, "weighted_agreement_percent"
    )

    strict_change = round(
        refined_strict - original_strict, 2
    )

    weighted_change = round(
        refined_weighted - original_weighted, 2
    )

    if strict_change > 0:
        status = "Improved"
    elif strict_change < 0:
        status = "Declined"
    else:
        status = "Unchanged"

    return {
        "app_id": original["app_id"],
        "app_name": original["app_name"],

        "original_strict_agreement": original_strict,
        "refined_strict_agreement": refined_strict,
        "strict_agreement_change": strict_change,

        "original_weighted_agreement": original_weighted,
        "refined_weighted_agreement": refined_weighted,
        "weighted_agreement_change": weighted_change,

        "status": status,

        "original_evaluated_fields": get_metric(
            original, "evaluated_fields"
        ),

        "refined_evaluated_fields": get_metric(
            refined, "evaluated_fields"
        )
    }


def generate_evaluation():

    print("\n" + "=" * 60)
    print("RESEARCH REFINEMENT EVALUATION")
    print("=" * 60)

    app_ids = get_application_ids()

    if not app_ids:
        print("No matching original and refined reports found.")
        return

    results = []

    for app_id in app_ids:

        original_path = (
            VERIFICATION_DIR
            / f"{app_id:03d}_comparison.json"
        )

        refined_path = (
            VERIFICATION_DIR
            / f"{app_id:03d}_refined_comparison.json"
        )

        try:
            original = load_json(original_path)
            refined = load_json(refined_path)

            result = calculate_improvement(
                original, refined
            )

            results.append(result)

            print(f"\nApplication: {result['app_name']}")

            print(
                f"Original strict agreement: "
                f"{result['original_strict_agreement']}%"
            )

            print(
                f"Refined strict agreement: "
                f"{result['refined_strict_agreement']}%"
            )

            print(
                f"Strict agreement change: "
                f"{result['strict_agreement_change']:+.2f} "
                "percentage points"
            )

            print(
                f"Original weighted agreement: "
                f"{result['original_weighted_agreement']}%"
            )

            print(
                f"Refined weighted agreement: "
                f"{result['refined_weighted_agreement']}%"
            )

            print(f"Status: {result['status']}")

        except Exception as error:
            print(
                f"\nERROR processing application {app_id}: {error}"
            )

    if not results:
        print("\nNo applications were successfully evaluated.")
        return

    # Aggregate statistics
    total_apps = len(results)

    improved = sum(
        1 for item in results
        if item["status"] == "Improved"
    )

    unchanged = sum(
        1 for item in results
        if item["status"] == "Unchanged"
    )

    declined = sum(
        1 for item in results
        if item["status"] == "Declined"
    )

    original_average = round(
        sum(
            item["original_strict_agreement"]
            for item in results
        ) / total_apps,
        2
    )

    refined_average = round(
        sum(
            item["refined_strict_agreement"]
            for item in results
        ) / total_apps,
        2
    )

    original_weighted_average = round(
        sum(
            item["original_weighted_agreement"]
            for item in results
        ) / total_apps,
        2
    )

    refined_weighted_average = round(
        sum(
            item["refined_weighted_agreement"]
            for item in results
        ) / total_apps,
        2
    )

    average_improvement = round(
        refined_average - original_average,
        2
    )

    average_weighted_improvement = round(
        refined_weighted_average - original_weighted_average,
        2
    )

    report = {
        "report_title": (
            "AppIntel Research Refinement Evaluation"
        ),

        "applications_evaluated": total_apps,
        "applications_improved": improved,
        "applications_unchanged": unchanged,
        "applications_declined": declined,

        "average_original_strict_agreement": original_average,
        "average_refined_strict_agreement": refined_average,
        "average_strict_agreement_change": average_improvement,

        "average_original_weighted_agreement": (
            original_weighted_average
        ),

        "average_refined_weighted_agreement": (
            refined_weighted_average
        ),

        "average_weighted_agreement_change": (
            average_weighted_improvement
        ),

        "application_results": results,

        "limitations": [
            "Evaluation currently covers only manually verified applications.",
            "Agreement percentages measure field-level agreement, not overall factual accuracy.",
            "Fields marked Needs review are excluded from comparison.",
            "Analyst-assessed fields are not independently verified vendor facts.",
            "Averages are calculated across applications, not weighted by evaluated field counts."
        ]
    }

    output_path = (
        OUTPUT_DIR / "refinement_evaluation.json"
    )

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(
            report,
            file,
            indent=4,
            ensure_ascii=False
        )

    # Display aggregate results
    print("\n" + "=" * 60)
    print("OVERALL REFINEMENT SUMMARY")
    print("=" * 60)

    print(f"Applications evaluated: {total_apps}")
    print(f"Improved: {improved}")
    print(f"Unchanged: {unchanged}")
    print(f"Declined: {declined}")

    print(
        f"\nAverage original strict agreement: "
        f"{original_average}%"
    )

    print(
        f"Average refined strict agreement: "
        f"{refined_average}%"
    )

    print(
        f"Average strict agreement change: "
        f"{average_improvement:+.2f} percentage points"
    )

    print(
        f"\nAverage original weighted agreement: "
        f"{original_weighted_average}%"
    )

    print(
        f"Average refined weighted agreement: "
        f"{refined_weighted_average}%"
    )

    print(
        f"Average weighted agreement change: "
        f"{average_weighted_improvement:+.2f} percentage points"
    )

    print(f"\nReport saved: {output_path}")


if __name__ == "__main__":
    generate_evaluation()
