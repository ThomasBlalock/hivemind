"""Emit a fake-but-plausible sweep CSV so the reporting pipeline can be smoke-tested.

The shape mirrors what ``scripts/run_harness_sweep.py`` produces. We bias the
distribution so ``hybrid_retrieval`` does slightly better than the baselines
on tasks for which a matching skill exists, and roughly equal elsewhere. This
makes the perf-vs-cost chart actually look like the project end-state when
inspected by the user.

    python scripts/synthesize_sweep_csv.py --out /tmp/fake_sweep.csv
"""

from __future__ import annotations

import argparse
import csv
import random
from pathlib import Path

# Three models at different cost tiers; mean cost-per-run differs.
MODELS = [
    ("openrouter/anthropic/claude-haiku-4.5", 0.02),
    ("openrouter/anthropic/claude-sonnet-4.6", 0.10),
    ("openrouter/anthropic/claude-opus-4.7", 0.35),
]

# Three policies; success-rate deltas applied per task type.
POLICIES = ["baseline_a@v1", "baseline_b@v1", "hybrid_retrieval@v1"]

# Tasks. Half have a "matching" skill; the rest don't.
TASKS = [
    ("fizzbuzz_off_by_one", True),
    ("regex_backref", True),
    ("sort_stability", True),
    ("misc_typo", False),
]

# Skills the synthesizer pretends are firing for the hybrid_retrieval policy
# when a matching skill exists.
HYBRID_SKILL_POOL = ["python-debugging", "regex-construction", "git-bisect"]


def _base_success_rate(model_idx: int) -> float:
    """Roughly: bigger model -> higher base success rate."""
    return [0.30, 0.55, 0.75][model_idx]


def _policy_lift(policy: str, task_has_match: bool) -> float:
    if policy == "hybrid_retrieval@v1":
        return 0.18 if task_has_match else 0.02
    if policy == "baseline_b@v1":
        return 0.06 if task_has_match else 0.0
    return 0.0


def _chunks_for(policy: str, task_has_match: bool, rng: random.Random) -> list[str]:
    if policy == "baseline_a@v1":
        return []
    if policy == "baseline_b@v1":
        return [rng.choice(HYBRID_SKILL_POOL)] if task_has_match else []
    # hybrid_retrieval: always returns top-3 candidates, but quality varies.
    if task_has_match:
        return list(HYBRID_SKILL_POOL)
    return [rng.choice(HYBRID_SKILL_POOL)]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--runs", type=int, default=3, help="Repeats per (task, model, policy) cell.")
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args(argv)

    rng = random.Random(args.seed)

    rows: list[dict] = []
    for run_idx in range(args.runs):
        for task_id, has_match in TASKS:
            for model_idx, (model, base_cost) in enumerate(MODELS):
                for policy in POLICIES:
                    sr = _base_success_rate(model_idx) + _policy_lift(policy, has_match)
                    sr = max(0.05, min(0.95, sr))
                    success = rng.random() < sr
                    # Cost jitter ±20%.
                    cost = base_cost * rng.uniform(0.8, 1.2)
                    chunk_ids = _chunks_for(policy, has_match, rng)
                    rows.append(
                        {
                            "run_idx": run_idx,
                            "task_id": task_id,
                            "model_arg": model,
                            "model": model,
                            "policy": policy,
                            "success": success,
                            "exit_status": "Submitted",
                            "cost_usd": round(cost, 4),
                            "n_calls": rng.randint(3, 12),
                            "n_chunks": len(chunk_ids),
                            "chunk_ids": ",".join(chunk_ids),
                            "error": "",
                            "submission": "",
                        }
                    )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "run_idx", "task_id", "model_arg", "model", "policy", "success", "exit_status",
        "cost_usd", "n_calls", "n_chunks", "chunk_ids", "error", "submission",
    ]
    with args.out.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(f"Wrote {len(rows)} synthetic rows to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
