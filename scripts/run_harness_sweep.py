"""Run the (task × model × policy) sweep against mini-swe-agent.

Real run:
    export OPENROUTER_API_KEY=sk-or-...
    python scripts/run_harness_sweep.py \\
        --models 'openrouter/anthropic/claude-haiku-4.5' 'openrouter/anthropic/claude-sonnet-4.6' \\
        --policies baseline_a baseline_b hybrid_retrieval \\
        --tasks eval_tasks/fizzbuzz_off_by_one eval_tasks/regex_backref \\
        --runs 1 \\
        --out runs/sweep_$(date +%s).csv

Dry run with deterministic fake model (no API key needed):
    python scripts/run_harness_sweep.py --dry-run
"""

from __future__ import annotations

import argparse
import csv
import os
import shutil
import sys
import tempfile
import time
from dataclasses import asdict
from pathlib import Path

import yaml
from dotenv import load_dotenv

# Pull OPENROUTER_API_KEY (and anything else) out of repo-root .env before
# the OPENROUTER_API_KEY check below runs.
load_dotenv()

from hivemind.harness.mini_swe_runner import HarnessResult, TaskSpec, run_task  # noqa: E402


def load_task(task_dir: Path) -> TaskSpec:
    spec = yaml.safe_load((task_dir / "task.yaml").read_text())
    return TaskSpec(
        id=spec["id"],
        prompt=spec["prompt"],
        work_dir=task_dir / "repo",  # may be overridden per-run with a tmpdir copy
        test_cmd=spec.get("test_cmd"),
        setup_cmd=spec.get("setup_cmd"),
    )


def _copy_task_to_tmp(task: TaskSpec, run_dir: Path) -> TaskSpec:
    """Each run gets a fresh copy of the repo so failed attempts don't poison
    later runs."""
    dest = run_dir / task.id / "repo"
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(task.work_dir, dest)
    return TaskSpec(
        id=task.id, prompt=task.prompt, work_dir=dest, test_cmd=task.test_cmd, setup_cmd=task.setup_cmd
    )


def _build_model(model_name: str, dry_run: bool):
    """Pick the right Model class for the model name. Falls back to a
    deterministic fake when --dry-run is set."""
    if dry_run:
        from minisweagent.models.test_models import DeterministicModel, make_output

        # Two-step fake: (1) inspect, (2) submit. Lets us prove the agent loop
        # boots and the system prompt was assembled correctly.
        outputs = [
            make_output(
                "THOUGHT: peek at the directory.",
                actions=[{"command": "ls"}],
                cost=0.001,
            ),
            make_output(
                "THOUGHT: complete the task.",
                actions=[{"command": "echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT"}],
                cost=0.001,
            ),
        ]
        return DeterministicModel(outputs=outputs)

    # Real run: route everything through litellm. OpenRouter is reached via
    # the `openrouter/<provider>/<model>` model-name convention.
    from minisweagent.models.litellm_model import LitellmModel
    return LitellmModel(model_name=model_name)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--models", nargs="+", default=["openrouter/anthropic/claude-haiku-4.5"])
    p.add_argument(
        "--policies", nargs="+", default=["baseline_a", "baseline_b", "hybrid_retrieval"]
    )
    p.add_argument("--tasks", nargs="+", default=["eval_tasks/fizzbuzz_off_by_one"])
    p.add_argument("--runs", type=int, default=1)
    p.add_argument("--step-limit", type=int, default=30)
    p.add_argument("--cost-limit", type=float, default=1.0)
    p.add_argument("--dynamic", action="store_true", help="Re-synthesize each turn (System 3 mode).")
    p.add_argument("--dry-run", action="store_true", help="Use DeterministicModel; no API calls.")
    p.add_argument("--out", default=None, help="CSV path; defaults to runs/sweep_<ts>.csv.")
    args = p.parse_args()

    if not args.dry_run and not os.environ.get("OPENROUTER_API_KEY"):
        print("ERROR: OPENROUTER_API_KEY not set (and --dry-run not specified).", file=sys.stderr)
        return 2

    out_path = Path(args.out or f"runs/sweep_{int(time.time())}.csv")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    base_tasks = [load_task(Path(t)) for t in args.tasks]
    rows: list[dict] = []

    with tempfile.TemporaryDirectory(prefix="hivemind_sweep_") as tmp:
        tmp_root = Path(tmp)
        for run_idx in range(args.runs):
            for task in base_tasks:
                isolated = _copy_task_to_tmp(task, tmp_root / f"run{run_idx}")
                for model_name in args.models:
                    for policy in args.policies:
                        # Rebuild the model per policy — DeterministicModel
                        # consumes its outputs list, so reusing across policies
                        # would shortchange later runs.
                        model = _build_model(model_name, args.dry_run)
                        print(f"[run {run_idx}] {task.id} | {model_name} | {policy} ...")
                        result: HarnessResult = run_task(
                            isolated,
                            model=model,
                            policy_name=policy,
                            step_limit=args.step_limit,
                            cost_limit_usd=args.cost_limit,
                            dynamic=args.dynamic,
                        )
                        row = asdict(result)
                        row["run_idx"] = run_idx
                        row["model_arg"] = model_name
                        rows.append(row)
                        print(
                            f"  ↳ success={result.success} cost=${result.cost_usd:.4f} "
                            f"calls={result.n_calls} chunks={result.n_chunks} ({','.join(result.chunk_ids) or '-'})"
                        )

    fields = [
        "run_idx", "task_id", "model_arg", "model", "policy", "success", "exit_status",
        "cost_usd", "n_calls", "n_chunks", "chunk_ids", "error", "submission",
    ]
    with out_path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            r = {**r, "chunk_ids": ",".join(r.get("chunk_ids", []))}
            w.writerow(r)
    print(f"\nWrote {len(rows)} rows to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
