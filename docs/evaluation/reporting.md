# Reporting

How sweep CSVs become a perf-vs-cost chart and a markdown summary.

## Inputs

`scripts/run_harness_sweep.py` emits a CSV with one row per `(run × task × model × policy)` cell:

| Column | Type | Notes |
|---|---|---|
| `run_idx` | int | 0-indexed repeat |
| `task_id` | str | matches `eval_tasks/<id>/task.yaml` |
| `model_arg`, `model` | str | OpenRouter routing string + canonical model name |
| `policy` | str | e.g. `hybrid_retrieval@v1` |
| `success` | bool | task's test command exit-code == 0 |
| `exit_status` | str | agent loop exit reason |
| `cost_usd` | float | from `agent.cost` (LiteLLM) |
| `n_calls`, `n_chunks` | int | model calls, injected skill chunks |
| `chunk_ids` | str | comma-joined skill ids actually injected |
| `error`, `submission` | str | optional |

## Pipeline

```
sweep CSV  ──▶ load_sweep_csv  ──▶ aggregate  ──▶ markdown_report  ──▶ report.md
                                            ╰──▶ perf_vs_cost_chart ─▶ perf_vs_cost.png
```

The public API lives in `src/hivemind/eval/report.py`:

- `load_sweep_csv(path) -> list[dict]` — parses + type-coerces; splits `chunk_ids` to a list.
- `aggregate(rows, *, baseline_policy="baseline_a@v1") -> dict` — returns `{by_cell, by_skill, pairwise, ...}`.
  - `by_cell`: one record per (model × policy) with `n_runs`, `n_tasks`, `success_rate`, `mean_cost`, `total_cost`, `mean_n_chunks`.
  - `by_skill`: per skill_id, `{n_fires, by_task, by_policy}` from the joined `chunk_ids` column.
  - `pairwise`: per (model, policy ≠ baseline), the per-task mean success-rate delta vs. the baseline policy, with a percentile-bootstrap 95% CI (1000 resamples).
- `markdown_report(agg, *, title=None) -> str` — headline, per-cell table, skill coverage table, pairwise deltas.
- `perf_vs_cost_chart(agg, out_png)` — matplotlib scatter: x = mean cost per run, y = success rate, colour = model, marker = policy.

## CLI

```bash
python scripts/build_report.py runs/sweep_<ts>.csv \
    --out-md runs/sweep_<ts>.report.md \
    --out-png runs/sweep_<ts>.perf_vs_cost.png \
    --baseline-policy baseline_a@v1
```

If `--out-md` / `--out-png` are omitted, both land next to the input CSV.

## Preview without running a real sweep

Cost-free dry-run — synthesizes a plausible CSV (3 models × 3 policies × 4 tasks × N runs)
and walks the full reporting pipeline:

```bash
python scripts/synthesize_sweep_csv.py --out /tmp/fake.csv --runs 3
python scripts/build_report.py /tmp/fake.csv --out-md /tmp/r.md --out-png /tmp/r.png
```

The synthesizer biases the distribution so `hybrid_retrieval` slightly beats baselines on
tasks with a matching skill, so the chart looks like the project's stated end-state
(CLAUDE.md, "End State") rather than noise.

## Choosing the baseline

`--baseline-policy` defaults to `baseline_a@v1` (no injection). Use that to read the
absolute lift from any injection method. Pass `--baseline-policy baseline_b@v1` to read the
lift relative to the state-of-practice keyword-trigger system.

## What's intentionally not in this module

- No live database; `runs/*.csv` is the source of truth.
- No statistical machinery beyond the percentile bootstrap (scipy isn't a dep).
- No per-skill ROI yet — that needs richer eval signal than success/fail and is on the
  System 2 / System 3 roadmap.
