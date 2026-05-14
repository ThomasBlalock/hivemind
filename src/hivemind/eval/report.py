"""Aggregate harness-sweep results into a perf-vs-cost report.

Input: a CSV produced by ``scripts/run_harness_sweep.py``. Columns:
    run_idx, task_id, model_arg, model, policy, success, exit_status,
    cost_usd, n_calls, n_chunks, chunk_ids (comma-joined), error, submission

Output: an aggregated dict (see :func:`aggregate`), a markdown report, and a
PNG scatter plot of success-rate vs. mean-cost-per-task.

Design choice: the project's stated end-state (CLAUDE.md) is the perf-vs-cost
chart, so this module is the production path for that artifact, not a stub.
See docs/evaluation/reporting.md.
"""

from __future__ import annotations

import csv
import statistics
from collections import defaultdict
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

import numpy as np

# Configuration anchored at the BaselineA policy name (no injection).
# Pairwise deltas are reported against this baseline by default.
DEFAULT_BASELINE_POLICY = "baseline_a@v1"

# Number of bootstrap resamples for pairwise CI. Cheap (no LM calls).
BOOTSTRAP_RESAMPLES = 1000


# --- IO --------------------------------------------------------------------


def _coerce_bool(s: str) -> bool:
    return str(s).strip().lower() in {"1", "true", "yes", "t"}


def _coerce_float(s: str, default: float = 0.0) -> float:
    if s is None or s == "":
        return default
    try:
        return float(s)
    except ValueError:
        return default


def _coerce_int(s: str, default: int = 0) -> int:
    if s is None or s == "":
        return default
    try:
        return int(s)
    except ValueError:
        return default


def load_sweep_csv(path: str | Path) -> list[dict]:
    """Parse a sweep CSV; coerce types; split chunk_ids back to a list.

    Returns rows ordered as in the file.
    """
    p = Path(path)
    rows: list[dict] = []
    with p.open(newline="") as f:
        reader = csv.DictReader(f)
        for raw in reader:
            chunk_ids_str = (raw.get("chunk_ids") or "").strip()
            chunk_ids = [c for c in chunk_ids_str.split(",") if c] if chunk_ids_str else []
            rows.append(
                {
                    "run_idx": _coerce_int(raw.get("run_idx", "0")),
                    "task_id": raw.get("task_id", ""),
                    "model_arg": raw.get("model_arg", ""),
                    "model": raw.get("model", ""),
                    "policy": raw.get("policy", ""),
                    "success": _coerce_bool(raw.get("success", "False")),
                    "exit_status": raw.get("exit_status", ""),
                    "cost_usd": _coerce_float(raw.get("cost_usd", "0")),
                    "n_calls": _coerce_int(raw.get("n_calls", "0")),
                    "n_chunks": _coerce_int(raw.get("n_chunks", "0")),
                    "chunk_ids": chunk_ids,
                    "error": raw.get("error", "") or "",
                    "submission": raw.get("submission", "") or "",
                }
            )
    return rows


# --- aggregation -----------------------------------------------------------


def _per_cell(rows: Sequence[dict]) -> list[dict]:
    """Group by (model, policy) and produce summary stats."""
    by_key: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for r in rows:
        by_key[(r["model"], r["policy"])].append(r)

    out: list[dict] = []
    for (model, policy), group in sorted(by_key.items()):
        n_runs = len(group)
        n_tasks = len({r["task_id"] for r in group})
        success_rate = sum(1 for r in group if r["success"]) / n_runs if n_runs else 0.0
        mean_cost = statistics.fmean([r["cost_usd"] for r in group]) if n_runs else 0.0
        total_cost = sum(r["cost_usd"] for r in group)
        mean_n_chunks = statistics.fmean([r["n_chunks"] for r in group]) if n_runs else 0.0
        out.append(
            {
                "model": model,
                "policy": policy,
                "n_runs": n_runs,
                "n_tasks": n_tasks,
                "success_rate": success_rate,
                "mean_cost": mean_cost,
                "total_cost": total_cost,
                "mean_n_chunks": mean_n_chunks,
            }
        )
    return out


def _by_skill(rows: Sequence[dict]) -> dict[str, dict]:
    """For each skill_id seen in any chunk_ids list, summarize how often it
    fired and where."""
    skills: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"n_fires": 0, "by_task": defaultdict(int), "by_policy": defaultdict(int)}
    )
    for r in rows:
        for sid in r["chunk_ids"]:
            skills[sid]["n_fires"] += 1
            skills[sid]["by_task"][r["task_id"]] += 1
            skills[sid]["by_policy"][r["policy"]] += 1
    # Convert defaultdicts to plain dicts for deterministic serialization.
    return {
        sid: {
            "n_fires": v["n_fires"],
            "by_task": dict(sorted(v["by_task"].items())),
            "by_policy": dict(sorted(v["by_policy"].items())),
        }
        for sid, v in sorted(skills.items())
    }


def _bootstrap_delta_ci(
    a_successes: Sequence[int],
    b_successes: Sequence[int],
    n_resamples: int = BOOTSTRAP_RESAMPLES,
    seed: int = 1,
) -> tuple[float, float]:
    """Percentile-bootstrap 95% CI on (mean(b) - mean(a)).

    Each input is the per-task success indicator (0/1) for one cell, paired
    by index. The CI is over the resampled task index.
    """
    if not a_successes or not b_successes or len(a_successes) != len(b_successes):
        return (0.0, 0.0)
    a = np.asarray(a_successes, dtype=np.float64)
    b = np.asarray(b_successes, dtype=np.float64)
    rng = np.random.default_rng(seed)
    n = len(a)
    idx = rng.integers(0, n, size=(n_resamples, n))
    deltas = b[idx].mean(axis=1) - a[idx].mean(axis=1)
    lo = float(np.percentile(deltas, 2.5))
    hi = float(np.percentile(deltas, 97.5))
    return (lo, hi)


def _pairwise_deltas(
    rows: Sequence[dict],
    baseline_policy: str,
) -> list[dict]:
    """Per (model, policy != baseline), report mean delta in success rate vs
    the baseline policy on the same (task_id) set, with a bootstrap CI.

    We pair by task_id and average over the per-task success rate, so models
    or policies that ran more times on one task don't unfairly weight it.
    """
    # First, average successes per (model, policy, task_id) into a single rate.
    cells: dict[tuple[str, str, str], list[int]] = defaultdict(list)
    for r in rows:
        cells[(r["model"], r["policy"], r["task_id"])].append(1 if r["success"] else 0)
    rate_per_task: dict[tuple[str, str, str], float] = {
        k: statistics.fmean(v) for k, v in cells.items()
    }

    out: list[dict] = []
    by_model_policy: dict[tuple[str, str], list[str]] = defaultdict(list)
    for (model, policy, task_id) in rate_per_task:
        by_model_policy[(model, policy)].append(task_id)

    for (model, policy), tasks in sorted(by_model_policy.items()):
        if policy == baseline_policy:
            continue
        base_tasks = sorted(set(by_model_policy.get((model, baseline_policy), [])) & set(tasks))
        if not base_tasks:
            continue
        a_rates = [rate_per_task[(model, baseline_policy, t)] for t in base_tasks]
        b_rates = [rate_per_task[(model, policy, t)] for t in base_tasks]
        # Bootstrap on integer-cast successes paired per task.
        a_int = [int(round(r)) for r in a_rates]
        b_int = [int(round(r)) for r in b_rates]
        lo, hi = _bootstrap_delta_ci(a_int, b_int)
        out.append(
            {
                "model": model,
                "policy": policy,
                "baseline": baseline_policy,
                "n_tasks": len(base_tasks),
                "mean_success_baseline": statistics.fmean(a_rates),
                "mean_success_policy": statistics.fmean(b_rates),
                "delta": statistics.fmean(b_rates) - statistics.fmean(a_rates),
                "ci95_lo": lo,
                "ci95_hi": hi,
            }
        )
    return out


def aggregate(
    rows: Iterable[dict],
    *,
    baseline_policy: str = DEFAULT_BASELINE_POLICY,
) -> dict:
    """Return aggregated stats: by_cell, by_skill, pairwise.

    See module docstring for the input schema. ``baseline_policy`` controls
    which cell pairwise deltas are computed against.
    """
    rows = list(rows)
    return {
        "n_rows": len(rows),
        "by_cell": _per_cell(rows),
        "by_skill": _by_skill(rows),
        "pairwise": _pairwise_deltas(rows, baseline_policy),
        "baseline_policy": baseline_policy,
    }


# --- markdown --------------------------------------------------------------


def _fmt_pct(x: float) -> str:
    return f"{100 * x:.1f}%"


def _fmt_money(x: float) -> str:
    return f"${x:.4f}"


def markdown_report(agg: dict, *, title: str | None = None) -> str:
    """Human-readable markdown summary of an aggregation."""
    lines: list[str] = []
    lines.append(f"# {title or 'HiveMind sweep report'}")
    lines.append("")

    # Headline: best cell by success rate (ties broken by lower cost).
    cells = agg["by_cell"]
    if cells:
        best = max(cells, key=lambda c: (c["success_rate"], -c["mean_cost"]))
        lines.append("## Headline")
        lines.append("")
        lines.append(
            f"- Top cell: **{best['model']} × {best['policy']}** at "
            f"{_fmt_pct(best['success_rate'])} success across {best['n_tasks']} task(s), "
            f"mean cost {_fmt_money(best['mean_cost'])}/run."
        )
        lines.append(f"- Total rows: {agg['n_rows']}")
        total_cost = sum(c["total_cost"] for c in cells)
        lines.append(f"- Total cost across all cells: {_fmt_money(total_cost)}")
        lines.append("")
    else:
        lines.append("_(no rows aggregated)_")
        lines.append("")

    # Per-cell table.
    lines.append("## Per-cell results")
    lines.append("")
    lines.append("| Model | Policy | n_runs | n_tasks | success_rate | mean_cost | mean_chunks |")
    lines.append("|---|---|---:|---:|---:|---:|---:|")
    for c in cells:
        lines.append(
            f"| {c['model']} | {c['policy']} | {c['n_runs']} | {c['n_tasks']} | "
            f"{_fmt_pct(c['success_rate'])} | {_fmt_money(c['mean_cost'])} | "
            f"{c['mean_n_chunks']:.1f} |"
        )
    lines.append("")

    # Skill coverage.
    lines.append("## Skill coverage")
    lines.append("")
    skills = agg["by_skill"]
    if not skills:
        lines.append("_(no skill chunks observed)_")
    else:
        lines.append("| Skill | n_fires | n_tasks | n_policies |")
        lines.append("|---|---:|---:|---:|")
        for sid, v in skills.items():
            lines.append(
                f"| {sid} | {v['n_fires']} | {len(v['by_task'])} | {len(v['by_policy'])} |"
            )
    lines.append("")

    # Pairwise deltas.
    lines.append("## Pairwise deltas vs baseline")
    lines.append("")
    lines.append(f"Baseline: `{agg['baseline_policy']}`")
    lines.append("")
    pw = agg["pairwise"]
    if not pw:
        lines.append("_(no comparable cells)_")
    else:
        lines.append(
            "| Model | Policy | n_tasks | baseline | policy | delta | CI95 |"
        )
        lines.append("|---|---|---:|---:|---:|---:|---|")
        for r in pw:
            lines.append(
                f"| {r['model']} | {r['policy']} | {r['n_tasks']} | "
                f"{_fmt_pct(r['mean_success_baseline'])} | "
                f"{_fmt_pct(r['mean_success_policy'])} | "
                f"{r['delta']:+.3f} | [{r['ci95_lo']:+.3f}, {r['ci95_hi']:+.3f}] |"
            )
    lines.append("")

    return "\n".join(lines)


# --- chart -----------------------------------------------------------------


# Cycle of marker symbols by policy index. Stable across runs so the user can
# eyeball comparisons between two reports.
_MARKER_CYCLE = ("o", "s", "^", "D", "P", "X", "v", "*")


def perf_vs_cost_chart(agg: dict, out_png: str | Path) -> Path:
    """Save a scatter plot of mean cost (x) vs success rate (y).

    Color = model. Marker = policy. Each point is one (model, policy) cell.
    """
    # Import lazily so the eval module is usable without matplotlib in
    # environments that only need aggregation.
    try:
        import matplotlib.pyplot as plt
    except ImportError as e:  # pragma: no cover
        raise RuntimeError(
            "matplotlib not installed. Install with: pip install -e '.[dev]'"
        ) from e

    out = Path(out_png)
    out.parent.mkdir(parents=True, exist_ok=True)

    cells = agg["by_cell"]
    fig, ax = plt.subplots(figsize=(8, 6))

    models = sorted({c["model"] for c in cells})
    policies = sorted({c["policy"] for c in cells})
    cmap = plt.get_cmap("tab10")
    model_color = {m: cmap(i % 10) for i, m in enumerate(models)}
    policy_marker = {p: _MARKER_CYCLE[i % len(_MARKER_CYCLE)] for i, p in enumerate(policies)}

    for c in cells:
        ax.scatter(
            c["mean_cost"],
            c["success_rate"],
            color=model_color[c["model"]],
            marker=policy_marker[c["policy"]],
            s=120,
            edgecolor="black",
            linewidth=0.5,
            zorder=3,
        )
        ax.annotate(
            f"{c['policy'].split('@')[0]}",
            (c["mean_cost"], c["success_rate"]),
            textcoords="offset points",
            xytext=(6, 6),
            fontsize=8,
            color="dimgray",
        )

    ax.set_xlabel("Mean cost per run (USD)")
    ax.set_ylabel("Success rate")
    ax.set_title("HiveMind: success vs. cost per (model × policy)")
    ax.set_ylim(-0.02, 1.05)
    ax.grid(True, alpha=0.3, zorder=0)

    # Two-axis legend: one for model color, one for policy marker.
    from matplotlib.lines import Line2D

    model_handles = [
        Line2D([0], [0], marker="o", color="w", markerfacecolor=model_color[m],
               markeredgecolor="black", markersize=9, label=m)
        for m in models
    ]
    policy_handles = [
        Line2D([0], [0], marker=policy_marker[p], color="black", linestyle="None",
               markersize=9, label=p)
        for p in policies
    ]
    leg1 = ax.legend(handles=model_handles, title="Model", loc="lower right", fontsize=8)
    ax.add_artist(leg1)
    ax.legend(handles=policy_handles, title="Policy", loc="upper left", fontsize=8)

    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out
