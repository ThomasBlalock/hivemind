"""Aggregate harness-sweep results into a perf-vs-cost report.

Input: a CSV produced by ``scripts/run_harness_sweep.py``. Columns:
    run_idx, task_id, model_arg, model, policy, success, exit_status,
    cost_usd, n_calls, n_chunks, chunk_ids (comma-joined), error, submission

Output: an aggregated dict (see :func:`aggregate`), a markdown report, and a
benchmark-table chart styled like an LLM release paper (dark background,
columns = (policy × base-model), rows = task-difficulty tiers + cost; best
column highlighted in blue).

Design choice: the project's stated end-state (CLAUDE.md) is a perf-vs-cost
view, so this module is the production path for that artifact. See
docs/evaluation/reporting.md.
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

    # Headline: best cell by success rate (ties broken by lower cost) and
    # spread vs the worst cell, so the reader can tell at a glance whether
    # policies are differentiating.
    cells = agg["by_cell"]
    if cells:
        best = max(cells, key=lambda c: (c["success_rate"], -c["mean_cost"]))
        worst = min(cells, key=lambda c: (c["success_rate"], -c["mean_cost"]))
        spread = best["success_rate"] - worst["success_rate"]
        lines.append("## Headline")
        lines.append("")
        lines.append(
            f"- Best cell: **{best['model']} × {best['policy']}** — "
            f"{_fmt_pct(best['success_rate'])} success across {best['n_tasks']} task(s), "
            f"mean cost {_fmt_money(best['mean_cost'])}/run."
        )
        lines.append(
            f"- Worst cell: **{worst['model']} × {worst['policy']}** — "
            f"{_fmt_pct(worst['success_rate'])} success "
            f"(spread vs best: {_fmt_pct(spread)})."
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


# Task → difficulty tier. Mirrors eval_tasks/README.md. Used to group rows in
# the benchmark-table chart.
TASK_TIERS: dict[str, str] = {
    # Easy
    "fizzbuzz_off_by_one": "Easy",
    "regex_backref": "Easy",
    "count_vowels_wrong_op": "Easy",
    "missing_return_factorial": "Easy",
    "negative_indices_clamp": "Easy",
    "strip_only_trailing": "Easy",
    # Medium
    "sort_by_length_stable": "Medium",
    "dict_default_mutability": "Medium",
    "parse_int_overflow": "Medium",
    "group_by_keyfn": "Medium",
    # Hard
    "sliding_window_avg": "Hard",
    "context_manager_leak": "Hard",
    "priority_queue_tiebreak": "Hard",
    "memoize_unhashable": "Hard",
}

_TIER_ORDER = ("Easy", "Medium", "Hard")


# Human-friendly short labels for column headers — release-paper style.
_POLICY_DISPLAY = {
    "baseline_a@v1": ("No Injection", "raw model, no skills"),
    "baseline_b@v1": ("Keyword Trigger", "current SOTA in OSS harnesses"),
    "hybrid_retrieval@v1": ("HiveMind Hybrid", "BM25 + dense + rerank"),
    "dspy_compiled@v1": ("HiveMind DSPy", "compiled distillations"),
    "online_bandit@v1": ("HiveMind Bandit", "LinUCB over hashed state"),
}


def _short_model(name: str) -> str:
    """Trim provider prefixes for tighter column headers."""
    last = name.rsplit("/", 1)[-1]
    return last.replace("claude-", "Claude ").replace("-", " ").title().replace("Claude ", "Claude ")


def _column_label(policy: str) -> tuple[str, str]:
    """Return (primary_label, subtitle) for a column header."""
    primary, subtitle = _POLICY_DISPLAY.get(policy, (policy.split("@")[0], ""))
    return primary, subtitle


def _per_tier_success(rows: Sequence[dict], policy: str, model: str) -> dict[str, float | None]:
    """Mean success rate per difficulty tier, plus 'Overall' and 'Mean cost'.

    Returns None for tiers with no rows so the table can render '—' instead
    of a misleading 0%.
    """
    tier_rows: dict[str, list[dict]] = {t: [] for t in _TIER_ORDER}
    all_rows: list[dict] = []
    for r in rows:
        if r["policy"] != policy or r["model"] != model:
            continue
        all_rows.append(r)
        tier = TASK_TIERS.get(r["task_id"])
        if tier:
            tier_rows[tier].append(r)
    out: dict[str, float | None] = {}
    for tier in _TIER_ORDER:
        group = tier_rows[tier]
        out[tier] = (sum(1 for r in group if r["success"]) / len(group)) if group else None
    out["Overall"] = (
        sum(1 for r in all_rows if r["success"]) / len(all_rows) if all_rows else None
    )
    out["Mean cost"] = statistics.fmean([r["cost_usd"] for r in all_rows]) if all_rows else None
    return out


_ROW_SPECS = (
    ("Easy", "Easy tier", "off-by-ones, simple bug fixes"),
    ("Medium", "Medium tier", "mutable defaults, parsing, grouping"),
    ("Hard", "Hard tier", "concurrency, memoization, heaps"),
    ("Overall", "Overall success", "all 14 tasks, mean of per-task success"),
    ("Mean cost", "Mean cost / run", "USD billed via OpenRouter"),
)


def _draw_panel(
    ax,
    *,
    panel_title: str,
    columns: list[dict],
    best_idx: int,
    show_header: bool,
) -> None:
    """Draw one (3-column-ish) sub-table onto ``ax``."""
    ax.set_facecolor("#0b0f14")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_axis_off()

    left_pad = 0.02
    right_pad = 0.02
    label_col_w = 0.28
    n_cols = len(columns)
    col_gap = 0.012
    data_w = 1 - left_pad - right_pad - label_col_w - col_gap * n_cols
    col_w = data_w / max(n_cols, 1)

    header_y = 0.86 if show_header else 0.93
    rows_top = 0.74 if show_header else 0.80
    rows_bot = 0.06
    n_rows = len(_ROW_SPECS)
    row_h = (rows_top - rows_bot) / n_rows

    # Panel title (the base-model name) along the left.
    if panel_title:
        ax.text(left_pad, 0.96, panel_title, transform=ax.transAxes,
                fontsize=12, color="#9ba6b2", ha="left", va="top", style="italic")

    # Column headers.
    if show_header:
        ax.text(left_pad, header_y, "Benchmark", transform=ax.transAxes,
                fontsize=11, color="#9ba6b2", ha="left", va="center")
    for i, col in enumerate(columns):
        x0 = left_pad + label_col_w + col_gap + i * (col_w + col_gap)
        x_center = x0 + col_w / 2
        is_best = (i == best_idx)
        color_primary = "#4ea1ff" if is_best else "#e6edf3"
        if show_header:
            ax.text(x_center, header_y + 0.04, col["primary"], transform=ax.transAxes,
                    fontsize=13, color=color_primary, weight="bold", ha="center", va="center")
            ax.text(x_center, header_y - 0.025, col["subtitle"], transform=ax.transAxes,
                    fontsize=9, color="#9ba6b2", ha="center", va="center")

    # Header divider.
    if show_header:
        ax.plot([left_pad, 1 - right_pad], [header_y - 0.07, header_y - 0.07],
                color="#2b3440", linewidth=1.2, transform=ax.transAxes)

    # Rows.
    for r_idx, (key, row_label, row_sub) in enumerate(_ROW_SPECS):
        y_center = rows_top - row_h * (r_idx + 0.5)

        ax.text(left_pad, y_center + row_h * 0.18, row_label, transform=ax.transAxes,
                fontsize=11.5, color="#e6edf3", ha="left", va="center", weight="bold")
        ax.text(left_pad, y_center - row_h * 0.20, row_sub, transform=ax.transAxes,
                fontsize=8.5, color="#7a8390", ha="left", va="center")

        if r_idx < n_rows - 1:
            y_div = y_center - row_h / 2
            ax.plot([left_pad, 1 - right_pad], [y_div, y_div],
                    color="#1a2027", linewidth=0.8, transform=ax.transAxes)

        for i, col in enumerate(columns):
            val = col["metrics"][key]
            x0 = left_pad + label_col_w + col_gap + i * (col_w + col_gap)
            x_center = x0 + col_w / 2
            is_best = (i == best_idx)
            color = "#4ea1ff" if is_best else "#e6edf3"
            if val is None:
                text = "—"
            elif key == "Mean cost":
                text = f"${val:.3f}"
            else:
                text = f"{100 * val:.1f}"
            ax.text(x_center, y_center, text, transform=ax.transAxes,
                    fontsize=20, color=color, ha="center", va="center",
                    weight="semibold" if is_best else "normal")


def benchmark_table_chart(
    agg_rows: Sequence[dict],
    out_png: str | Path,
    *,
    title: str = "HiveMind: context injection on bug-fix tasks",
) -> Path:
    """Render a release-paper-style benchmark table.

    One panel per base model. Within each panel: columns = injection policies
    (No Injection / Keyword Trigger / HiveMind Hybrid / ...), rows = task
    difficulty tiers + Overall success + Mean cost. The strongest column in
    each panel is highlighted in blue, à la *Muse Spark Contemplating* in the
    reference shot.
    """
    try:
        import matplotlib.pyplot as plt
    except ImportError as e:  # pragma: no cover
        raise RuntimeError(
            "matplotlib not installed. Install with: pip install -e '.[dev]'"
        ) from e

    out = Path(out_png)
    out.parent.mkdir(parents=True, exist_ok=True)

    cells: list[tuple[str, str]] = sorted({(r["model"], r["policy"]) for r in agg_rows})
    if not cells:
        fig, ax = plt.subplots(figsize=(8, 3), facecolor="#0b0f14")
        ax.set_facecolor("#0b0f14")
        ax.text(0.5, 0.5, "No data", color="#cccccc", ha="center", va="center", fontsize=16)
        ax.set_axis_off()
        fig.savefig(out, dpi=160, facecolor=fig.get_facecolor())
        plt.close(fig)
        return out

    # Group by base model; one panel per model.
    models = sorted({m for m, _ in cells})

    panels: list[dict] = []
    for model in models:
        cols = []
        for policy in sorted({p for m, p in cells if m == model}):
            primary, subtitle = _column_label(policy)
            cols.append({
                "policy": policy,
                "primary": primary,
                "subtitle": subtitle,
                "metrics": _per_tier_success(agg_rows, policy=policy, model=model),
            })

        def _score(col: dict) -> tuple[float, float]:
            ov = col["metrics"]["Overall"] or 0.0
            mc = col["metrics"]["Mean cost"] or 0.0
            return (ov, -mc)

        best_idx = max(range(len(cols)), key=lambda i: _score(cols[i]))
        panels.append({"model": model, "columns": cols, "best_idx": best_idx})

    # Figure: one row per panel, title row at the top.
    n_panels = len(panels)
    fig_w = 12.0
    fig_h = 1.4 + 4.2 * n_panels
    fig, axes = plt.subplots(
        n_panels + 1, 1,
        figsize=(fig_w, fig_h),
        facecolor="#0b0f14",
        gridspec_kw={"height_ratios": [0.5] + [4.0] * n_panels, "hspace": 0.15},
    )
    if n_panels + 1 == 1:
        axes = [axes]

    # Title strip.
    title_ax = axes[0]
    title_ax.set_facecolor("#0b0f14")
    title_ax.set_axis_off()
    title_ax.text(0.02, 0.55, title, transform=title_ax.transAxes,
                  fontsize=16, color="#e6edf3", weight="bold", ha="left", va="center")
    title_ax.text(0.02, 0.05, "Bug-fix tasks across 14 self-contained repos. "
                              "Columns are context-injection policies; rows are difficulty tiers.",
                  transform=title_ax.transAxes, fontsize=10, color="#7a8390",
                  ha="left", va="center")

    for i, panel in enumerate(panels):
        _draw_panel(
            axes[i + 1],
            panel_title=_short_model(panel["model"]),
            columns=panel["columns"],
            best_idx=panel["best_idx"],
            show_header=True,
        )

    fig.savefig(out, dpi=170, facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close(fig)
    return out


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
