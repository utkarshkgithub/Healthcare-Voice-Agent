"""
Triage evaluation harness.

Measures the pipeline's routing decisions against the golden set and reports
the metric that matters in triage: emergency false negatives.

    # with a real key configured
    python -m evals.run_eval

    # deterministic layers only, no network, no API cost
    python -m evals.run_eval --offline

The --offline mode evaluates exactly the deterministic layer, which is how you
prove the safety net works without depending on a model being reachable. A
regression there is a genuine safety regression; the LLM's contribution on top
is measured separately.
"""
import argparse
import os
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evals.golden_cases import GOLDEN_CASES, Case  # noqa: E402
from red_flags import detect_red_flags  # noqa: E402


def evaluate_rules(cases: list[Case]) -> dict:
    """Score the deterministic red-flag layer alone."""
    results = []
    for case in cases:
        flagged = detect_red_flags(case.utterance)
        escalated = bool(flagged)
        results.append(
            {
                "case": case,
                "escalated": escalated,
                "expected": case.is_emergency,
                "correct": escalated == case.is_emergency,
                "flags": flagged,
            }
        )
    return _summarise(results)


def evaluate_llm(cases: list[Case]) -> dict:
    """
    Score the full pipeline: the deterministic layer OR the model's verdict.

    This is the number that describes the deployed system.
    """
    from llm.factory import LLMProviderFactory

    llm = LLMProviderFactory.create()
    results = []
    for case in cases:
        rule_flags = detect_red_flags(case.utterance)
        escalated = bool(rule_flags)
        via = "rules"

        if not escalated:
            raw = llm.call_prompt("chat_check_emergency", symptoms=case.utterance)
            escalated = "YES" in raw.upper()
            via = "llm"

        results.append(
            {
                "case": case,
                "escalated": escalated,
                "expected": case.is_emergency,
                "correct": escalated == case.is_emergency,
                "flags": rule_flags,
                "via": via,
            }
        )
    return _summarise(results)


def _summarise(results: list[dict]) -> dict:
    true_emergencies = [r for r in results if r["expected"]]
    true_emergencies = true_emergencies or []
    non_emergencies = [r for r in results if not r["expected"]]

    # The metric that matters: of the cases that genuinely are emergencies,
    # how many did we fail to escalate?
    missed = [r for r in true_emergencies if not r["escalated"]]
    over_escalated = [r for r in non_emergencies if r["escalated"]]

    total = len(results) or 1
    return {
        "total": len(results),
        "accuracy": sum(r["correct"] for r in results) / total,
        "true_emergencies": len(true_emergencies),
        "missed_emergencies": len(missed),
        "false_negative_rate": len(missed) / (len(true_emergencies) or 1),
        "false_positives": len(over_escalated),
        "false_positive_rate": len(over_escalated) / (len(non_emergencies) or 1),
        "results": results,
        "by_source": Counter(r.get("via", "rules") for r in results),
    }


def report(name: str, summary: dict, show_failures: bool = True) -> None:
    print(f"\n{'=' * 62}")
    print(f"  {name}")
    print(f"{'=' * 62}")
    print(f"  cases                  {summary['total']}")
    print(f"  accuracy               {summary['accuracy']:.1%}")
    print(f"  true emergencies       {summary['true_emergencies']}")
    print(f"  MISSED emergencies     {summary['missed_emergencies']}")
    print(f"  false-negative rate    {summary['false_negative_rate']:.1%}   <- headline metric")
    print(f"  false escalations      {summary['false_positives']} ({summary['false_positive_rate']:.1%})")
    if summary["by_source"]:
        print(f"  escalated by           {dict(summary['by_source'])}")

    if show_failures:
        failures = [r for r in summary["results"] if not r["correct"]]
        if failures:
            print(f"\n  Failures:")
            for failure in failures:
                kind = "MISSED" if failure["expected"] else "OVER-CALLED"
                print(f"    [{kind}] {failure['case'].utterance!r}")
                print(f"             {failure['case'].note}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the triage golden set.")
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Score only the deterministic rules layer. No network, no cost.",
    )
    parser.add_argument(
        "--fail-under",
        type=float,
        default=None,
        help="Exit non-zero if the false-negative rate exceeds this. Use in CI.",
    )
    args = parser.parse_args()

    report("Deterministic red-flag layer (offline)", evaluate_rules(GOLDEN_CASES))

    worst_case_fnr = None
    if not args.offline:
        from dotenv import load_dotenv

        load_dotenv()

        provider = os.getenv("LLM_PROVIDER", "openai")
        required = {
            "openai": "OPENAI_API_KEY",
            "gemini": "GEMINI_API_KEY",
            "cerebras": "CEREBRAS_API_KEY",
        }.get(provider, "OPENAI_API_KEY")

        if not os.getenv(required):
            print(f"\n  LLM evaluation skipped: {required} is not set")
        else:
            try:
                summary = evaluate_llm(GOLDEN_CASES)
                report(f"Full pipeline (LLM_PROVIDER={provider})", summary)
                worst_case_fnr = summary["false_negative_rate"]
            except Exception as exc:
                print(f"\n  LLM evaluation skipped: {exc}")

    if args.fail_under is not None:
        offline_fnr = evaluate_rules(GOLDEN_CASES)["false_negative_rate"]
        observed = max(filter(None, [offline_fnr, worst_case_fnr]))
        if observed > args.fail_under:
            print(f"\nFAIL false-negative rate {observed:.1%} exceeds {args.fail_under:.1%}")
            return 1
        print(f"\nOK false-negative rate {observed:.1%} within {args.fail_under:.1%}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())