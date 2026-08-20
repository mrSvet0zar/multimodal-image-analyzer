"""Run the golden eval suite against the live Claude Vision service.

Scores each analysis against known ground truth and prints a report with an
aggregate quality score, cost, and a pass/fail gate (for CI or manual runs).

Usage (from backend/, with ANTHROPIC_API_KEY set):
    python -m evals.run_evals [--threshold 0.75] [--json report.json]

Exit codes: 0 = suite passed, 1 = below threshold, 2 = misconfigured (no key).
"""

import argparse
import asyncio
import json
import sys

from app.config import settings
from app.vision_service import VisionAnalyzer
from evals.cases import CASES, EvalCase


def _haystack(analysis: dict) -> str:
    parts = [analysis.get("description", ""), analysis.get("sentiment", "")]
    parts += [str(t) for t in analysis.get("tags", [])]
    parts += [str(o.get("name", "")) for o in analysis.get("objects", []) if isinstance(o, dict)]
    return " ".join(parts).lower()


def score_case(case: EvalCase, analysis: dict) -> tuple[float, list[str]]:
    """Return (score in [0,1], list of failed-check labels)."""
    checks: list[bool] = []
    failures: list[str] = []

    if case.expected_text is not None:
        ok = case.expected_text.lower() in analysis.get("extracted_text", "").lower()
        checks.append(ok)
        if not ok:
            failures.append(f"text~'{case.expected_text}'")

    haystack = _haystack(analysis)
    for kw in case.expected_keywords:
        ok = kw.lower() in haystack
        checks.append(ok)
        if not ok:
            failures.append(f"kw:{kw}")

    score = sum(checks) / len(checks) if checks else 1.0
    return score, failures


async def run(threshold: float, json_path: str | None) -> int:
    if not settings.anthropic_api_key:
        print("ANTHROPIC_API_KEY not set — cannot run evals.", file=sys.stderr)
        return 2

    analyzer = VisionAnalyzer()
    results = []
    total_cost = 0.0

    print(f"\nRunning {len(CASES)} eval cases against {settings.vision_model}\n")
    print(f"{'case':<26} {'score':>6}  {'cost':>9}  failures")
    print("-" * 72)

    for case in CASES:
        analysis, usage = await analyzer.analyze_image(
            case.image_bytes(), media_type="image/jpeg", detail_level="medium"
        )
        score, failures = score_case(case, analysis)
        total_cost += usage["cost_usd"]
        results.append({"id": case.id, "score": round(score, 3), "failures": failures})
        mark = "OK " if score >= 0.999 else ("~  " if score >= 0.5 else "X  ")
        print(
            f"{mark}{case.id:<23} {score:>6.0%}  ${usage['cost_usd']:>7.4f}  "
            f"{', '.join(failures) if failures else '-'}"
        )

    suite_score = sum(r["score"] for r in results) / len(results)
    passed = suite_score >= threshold

    print("-" * 72)
    print(
        f"SUITE SCORE: {suite_score:.1%}  (threshold {threshold:.0%})  "
        f"total cost ${total_cost:.4f}  -> {'PASS' if passed else 'FAIL'}\n"
    )

    if json_path:
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "model": settings.vision_model,
                    "suite_score": round(suite_score, 4),
                    "threshold": threshold,
                    "passed": passed,
                    "total_cost_usd": round(total_cost, 6),
                    "cases": results,
                },
                f,
                indent=2,
            )
        print(f"Wrote JSON report to {json_path}")

    return 0 if passed else 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Vision eval suite.")
    parser.add_argument("--threshold", type=float, default=0.75)
    parser.add_argument("--json", dest="json_path", default=None)
    args = parser.parse_args()
    sys.exit(asyncio.run(run(args.threshold, args.json_path)))


if __name__ == "__main__":
    main()
