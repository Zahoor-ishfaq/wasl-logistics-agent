"""
eval/compare.py

Compares the latest evaluation run against the committed baseline and
fails (non-zero exit) if quality regressed beyond a threshold. This is
the release gate — wired into CI, it stops a change that quietly makes
answers worse from being merged.

    python eval/compare.py

Exit codes:
    0  latest is >= baseline (within tolerance)
    1  a regression exceeded the tolerance
    2  missing files / setup problem

To set a new baseline (after an intended improvement):
    python eval/compare.py --set-baseline
"""

import json
import sys
from pathlib import Path

RESULTS_DIR = Path(__file__).resolve().parent / "results"
LATEST = RESULTS_DIR / "latest.json"
BASELINE = RESULTS_DIR / "baseline.json"

# How much a metric may drop before it's a regression.
TOLERANCE = 0.05  # 5 percentage points


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def flatten(summary: dict) -> dict[str, float]:
    """Pull the comparable scalar metrics out of a results summary."""
    m = {"overall_pass_rate": summary.get("overall_pass_rate", 0.0)}
    for t, s in (summary.get("by_type") or {}).items():
        m[f"pass_rate_{t}"] = s.get("pass_rate", 0.0)
    for k, v in (summary.get("ragas") or {}).items():
        if v is not None:
            m[f"ragas_{k}"] = v
    return m


def main() -> None:
    if "--set-baseline" in sys.argv:
        if not LATEST.exists():
            print("No latest.json to promote. Run run_eval.py first.")
            sys.exit(2)
        BASELINE.write_text(LATEST.read_text(encoding="utf-8"), encoding="utf-8")
        print("Baseline updated from latest.json.")
        sys.exit(0)

    if not LATEST.exists():
        print("No latest.json found. Run: python eval/run_eval.py")
        sys.exit(2)

    if not BASELINE.exists():
        # First run — promote latest to baseline and pass.
        BASELINE.write_text(LATEST.read_text(encoding="utf-8"), encoding="utf-8")
        print("No baseline existed; created one from the current run. Passing.")
        sys.exit(0)

    latest = flatten(load(LATEST))
    baseline = flatten(load(BASELINE))

    print("Metric comparison (latest vs baseline):")
    print("-" * 56)
    regressed = []
    for key in sorted(set(latest) | set(baseline)):
        lv = latest.get(key)
        bv = baseline.get(key)
        if lv is None or bv is None:
            print(f"  {key:28s}  {str(bv):>7} -> {str(lv):>7}  (n/a)")
            continue
        delta = lv - bv
        flag = ""
        if delta < -TOLERANCE:
            flag = "  <-- REGRESSION"
            regressed.append((key, bv, lv, delta))
        print(f"  {key:28s}  {bv:6.3f} -> {lv:6.3f}  ({delta:+.3f}){flag}")

    print("-" * 56)
    if regressed:
        print(
            f"\nFAIL: {len(regressed)} metric(s) regressed beyond tolerance ({TOLERANCE})."
        )
        for key, bv, lv, delta in regressed:
            print(f"  {key}: {bv:.3f} -> {lv:.3f} ({delta:+.3f})")
        sys.exit(1)

    print("\nPASS: no regressions beyond tolerance.")
    sys.exit(0)


if __name__ == "__main__":
    main()
