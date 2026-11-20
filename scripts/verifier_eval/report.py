"""Print the verifier evaluation as Markdown (issue #59). Offline: reads the committed set only.

Usage: uv run python scripts/verifier_eval/report.py
"""

from __future__ import annotations

import sys

from receipts.verify.evaluation import (
    PRECISION_FLOOR,
    RECALL_FLOOR,
    Rate,
    evaluate,
    load,
    stored_precision,
)


def _rate(rate: Rate) -> str:
    low, high = rate.interval
    return f"{rate.hits} of {rate.total} ({rate.value:.1%}; 95% CI {low:.1%} to {high:.1%})"


def main() -> int:
    rows = load()
    report = evaluate(rows)
    print(f"Re-run rows: {report.rows} (of {len(rows)} labeled; the rest are stored runs)\n")
    print("| Measure | Value | CI floor |")
    print("|---|---|---|")
    print(f"| Precision | {_rate(report.precision)} | {PRECISION_FLOOR:.0%} |")
    print(f"| Recall | {_rate(report.recall)} | {RECALL_FLOOR:.0%} |")
    for method, rate in report.false_verified_by_method.items():
        print(f"| Verified but not backed, `{method}` | {rate.hits} of {rate.total} | |")
    for domain, rate in report.false_verified_by_domain.items():
        print(f"| Verified but not backed, {domain} | {rate.hits} of {rate.total} | |")
    print(
        f"| Failing claims Mellea rewrote | {report.rewritten.hits} of {report.rewritten.total} | |"
    )
    print(
        f"| Rewrites labeled supported | {report.rewrites_supported.hits} of "
        f"{report.rewrites_supported.total} | |"
    )
    print(f"| Stored runs, verdict as shipped | {_rate(stored_precision(rows))} | |")
    print("\n| Label | Verified | Not verified |")
    print("|---|---|---|")
    for label in ("supported", "unsupported", "wrong"):
        yes = report.confusion.get((label, True), 0)
        no = report.confusion.get((label, False), 0)
        print(f"| {label} | {yes} | {no} |")
    if report.changed:
        print(f"\nVerdicts that changed since recording: {', '.join(report.changed)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
