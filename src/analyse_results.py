from pathlib import Path
from collections import Counter

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RESULTS_DIR = BASE_DIR / "results"

EVALUATIONS_FILE = DATA_DIR / "evaluations.csv"
RESPONSES_FILE = DATA_DIR / "model_responses.csv"

SCORE_COLUMNS = [
    "factual_accuracy",
    "instruction_following",
    "reasoning_quality",
    "relevance",
    "helpfulness",
    "completeness",
    "safety",
    "language_quality",
    "user_intent_alignment",
]


def load_data():
    evaluations = pd.read_csv(EVALUATIONS_FILE)
    responses = pd.read_csv(RESPONSES_FILE)

    merged = evaluations.merge(
        responses[["response_id", "model_id"]],
        on="response_id",
        how="left",
    )

    return merged


def calculate_model_scores(df):
    return (
        df.groupby("model_id")["overall_score"]
        .agg(["count", "mean", "min", "max"])
        .round(2)
        .sort_values("mean", ascending=False)
    )


def calculate_dimension_scores(df):
    scores = df[SCORE_COLUMNS].mean().sort_values(ascending=False)
    return scores.round(2)


def calculate_hallucination_rate(df):
    hallucinations = (
        df["hallucination_detected"]
        .astype(str)
        .str.strip()
        .str.lower()
        .eq("yes")
    )

    return round(hallucinations.mean() * 100, 2)


def calculate_instruction_failure_rate(df):
    failures = (
        df["failure_labels"]
        .fillna("")
        .str.contains("INSTRUCTION_FAILURE", regex=False)
    )

    return round(failures.mean() * 100, 2)


def calculate_preference_results(df):
    preferred = df[df["preference_rank"] == 1]

    return (
        preferred.groupby("model_id")
        .size()
        .sort_values(ascending=False)
        .rename("preferred_responses")
    )


def count_failure_labels(df):
    labels = []

    for value in df["failure_labels"].dropna():
        for label in str(value).split(";"):
            label = label.strip()
            if label:
                labels.append(label)

    return pd.Series(Counter(labels)).sort_values(ascending=False)


def create_summary(df):
    total_responses = len(df)
    average_score = round(df["overall_score"].mean(), 2)
    hallucination_rate = calculate_hallucination_rate(df)
    instruction_failure_rate = calculate_instruction_failure_rate(df)

    return {
        "total_evaluated_responses": total_responses,
        "average_overall_score": average_score,
        "hallucination_rate_percent": hallucination_rate,
        "instruction_failure_rate_percent": instruction_failure_rate,
    }


def save_results(
    summary,
    model_scores,
    dimension_scores,
    preference_results,
    failure_counts,
):
    RESULTS_DIR.mkdir(exist_ok=True)

    model_scores.to_csv(RESULTS_DIR / "model_score_summary.csv")
    dimension_scores.to_csv(
        RESULTS_DIR / "dimension_score_summary.csv",
        header=["average_score"],
    )
    preference_results.to_csv(
        RESULTS_DIR / "preference_summary.csv",
        header=True,
    )
    failure_counts.to_csv(
        RESULTS_DIR / "failure_label_summary.csv",
        header=["count"],
    )

    summary_df = pd.DataFrame(
        list(summary.items()),
        columns=["metric", "value"],
    )
    summary_df.to_csv(
        RESULTS_DIR / "benchmark_summary.csv",
        index=False,
    )


def print_report(
    summary,
    model_scores,
    dimension_scores,
    preference_results,
    failure_counts,
):
    print("\nLLM EVALUATION BENCHMARK REPORT")
    print("=" * 40)

    print("\nOverall benchmark summary")
    print("-" * 40)

    for metric, value in summary.items():
        print(f"{metric}: {value}")

    print("\nModel performance")
    print("-" * 40)
    print(model_scores)

    print("\nAverage score by evaluation dimension")
    print("-" * 40)
    print(dimension_scores)

    print("\nPreference ranking results")
    print("-" * 40)
    print(preference_results)

    print("\nMost common failure labels")
    print("-" * 40)

    if failure_counts.empty:
        print("No failure labels recorded.")
    else:
        print(failure_counts)


def main():
    df = load_data()

    summary = create_summary(df)
    model_scores = calculate_model_scores(df)
    dimension_scores = calculate_dimension_scores(df)
    preference_results = calculate_preference_results(df)
    failure_counts = count_failure_labels(df)

    print_report(
        summary,
        model_scores,
        dimension_scores,
        preference_results,
        failure_counts,
    )

    save_results(
        summary,
        model_scores,
        dimension_scores,
        preference_results,
        failure_counts,
    )

    print("\nAnalysis complete.")
    print("Results saved to the results/ directory.")


if __name__ == "__main__":
    main()
