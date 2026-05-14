"""Build a markdown + PNG report from a sweep CSV.

    python scripts/build_report.py <sweep_csv> [--out-md report.md] [--out-png perf_vs_cost.png]

Defaults: write outputs next to the input CSV.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from hivemind.eval.report import (
    aggregate,
    load_sweep_csv,
    markdown_report,
    perf_vs_cost_chart,
)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("sweep_csv", type=Path)
    p.add_argument("--out-md", type=Path, default=None)
    p.add_argument("--out-png", type=Path, default=None)
    p.add_argument(
        "--baseline-policy",
        default="baseline_a@v1",
        help="Policy name used as the comparison baseline for pairwise deltas.",
    )
    p.add_argument("--title", default=None)
    args = p.parse_args(argv)

    if not args.sweep_csv.exists():
        print(f"ERROR: {args.sweep_csv} not found.", file=sys.stderr)
        return 2

    out_md = args.out_md or args.sweep_csv.with_suffix(".report.md")
    out_png = args.out_png or args.sweep_csv.with_suffix(".perf_vs_cost.png")

    rows = load_sweep_csv(args.sweep_csv)
    agg = aggregate(rows, baseline_policy=args.baseline_policy)
    md = markdown_report(agg, title=args.title or f"Sweep report: {args.sweep_csv.name}")

    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(md)
    print(f"Wrote markdown report: {out_md}")

    chart_path = perf_vs_cost_chart(agg, out_png)
    print(f"Wrote chart: {chart_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
