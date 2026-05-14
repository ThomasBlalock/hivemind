"""Aggregate per-task results into the perf-vs-cost report.

Reads Inspect AI's eval log directory + the LiteLLM cost sqlite (when present)
and emits a CSV at runs/<timestamp>/cost.csv. See docs/evaluation/cost_tracking.md.

Scaffolded; assumes Inspect AI's log format. Will need adjustment to the real
log schema once the eval harness is actually invoked.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path


def write_report(log_dir: Path, out_csv: Path) -> Path:
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    for log_file in sorted(log_dir.glob("*.json")):
        try:
            with log_file.open() as f:
                data = json.load(f)
        except json.JSONDecodeError:
            continue
        rows.append(
            {
                "task": data.get("task"),
                "model": data.get("model"),
                "policy": data.get("metadata", {}).get("policy"),
                "success_rate": data.get("results", {}).get("score"),
                "tokens_in": data.get("usage", {}).get("input_tokens"),
                "tokens_out": data.get("usage", {}).get("output_tokens"),
                "cost_usd": data.get("usage", {}).get("cost"),
            }
        )

    fields = ["task", "model", "policy", "success_rate", "tokens_in", "tokens_out", "cost_usd"]
    with out_csv.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    return out_csv
