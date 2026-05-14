"""Tests for hivemind.eval.report and the supporting CLI scripts."""

from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path

from hivemind.eval.report import (
    aggregate,
    load_sweep_csv,
    markdown_report,
    perf_vs_cost_chart,
)

REPO = Path(__file__).resolve().parents[1]


def _write_csv(path: Path, rows: list[dict]) -> Path:
    fields = [
        "run_idx", "task_id", "model_arg", "model", "policy", "success", "exit_status",
        "cost_usd", "n_calls", "n_chunks", "chunk_ids", "error", "submission",
    ]
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            r = {**r, "chunk_ids": ",".join(r.get("chunk_ids", []) or [])}
            w.writerow(r)
    return path


def _sample_rows() -> list[dict]:
    return [
        # haiku × baseline_a × 2 tasks × 2 runs (~30% success)
        {"run_idx": 0, "task_id": "t1", "model_arg": "haiku", "model": "haiku",
         "policy": "baseline_a@v1", "success": True, "exit_status": "Submitted",
         "cost_usd": 0.02, "n_calls": 4, "n_chunks": 0, "chunk_ids": []},
        {"run_idx": 1, "task_id": "t1", "model_arg": "haiku", "model": "haiku",
         "policy": "baseline_a@v1", "success": False, "exit_status": "Submitted",
         "cost_usd": 0.02, "n_calls": 4, "n_chunks": 0, "chunk_ids": []},
        {"run_idx": 0, "task_id": "t2", "model_arg": "haiku", "model": "haiku",
         "policy": "baseline_a@v1", "success": False, "exit_status": "Submitted",
         "cost_usd": 0.02, "n_calls": 4, "n_chunks": 0, "chunk_ids": []},
        {"run_idx": 1, "task_id": "t2", "model_arg": "haiku", "model": "haiku",
         "policy": "baseline_a@v1", "success": False, "exit_status": "Submitted",
         "cost_usd": 0.02, "n_calls": 4, "n_chunks": 0, "chunk_ids": []},

        # haiku × hybrid_retrieval × 2 tasks × 2 runs (~75%)
        {"run_idx": 0, "task_id": "t1", "model_arg": "haiku", "model": "haiku",
         "policy": "hybrid_retrieval@v1", "success": True, "exit_status": "Submitted",
         "cost_usd": 0.025, "n_calls": 5, "n_chunks": 3,
         "chunk_ids": ["regex", "python-debug", "bisect"]},
        {"run_idx": 1, "task_id": "t1", "model_arg": "haiku", "model": "haiku",
         "policy": "hybrid_retrieval@v1", "success": True, "exit_status": "Submitted",
         "cost_usd": 0.025, "n_calls": 5, "n_chunks": 3,
         "chunk_ids": ["regex", "python-debug", "bisect"]},
        {"run_idx": 0, "task_id": "t2", "model_arg": "haiku", "model": "haiku",
         "policy": "hybrid_retrieval@v1", "success": True, "exit_status": "Submitted",
         "cost_usd": 0.025, "n_calls": 5, "n_chunks": 2,
         "chunk_ids": ["regex", "python-debug"]},
        {"run_idx": 1, "task_id": "t2", "model_arg": "haiku", "model": "haiku",
         "policy": "hybrid_retrieval@v1", "success": False, "exit_status": "Submitted",
         "cost_usd": 0.025, "n_calls": 5, "n_chunks": 2,
         "chunk_ids": ["regex", "python-debug"]},
    ]


def test_load_sweep_csv_roundtrip(tmp_path: Path):
    rows = _sample_rows()
    csv_path = _write_csv(tmp_path / "sweep.csv", rows)
    loaded = load_sweep_csv(csv_path)
    assert len(loaded) == len(rows)
    # chunk_ids must come back as a list, not a comma-joined string.
    assert isinstance(loaded[0]["chunk_ids"], list)
    # Type coercions.
    assert isinstance(loaded[0]["success"], bool)
    assert isinstance(loaded[0]["cost_usd"], float)
    assert isinstance(loaded[0]["n_chunks"], int)
    # A row with non-empty chunk_ids comes back as a list.
    h = next(r for r in loaded if r["policy"] == "hybrid_retrieval@v1")
    assert "regex" in h["chunk_ids"]


def test_aggregate_basic_shape():
    rows = _sample_rows()
    agg = aggregate(rows)
    # 2 cells: (haiku, baseline_a) and (haiku, hybrid_retrieval).
    cells = {(c["model"], c["policy"]): c for c in agg["by_cell"]}
    assert ("haiku", "baseline_a@v1") in cells
    assert ("haiku", "hybrid_retrieval@v1") in cells
    base = cells[("haiku", "baseline_a@v1")]
    hyb = cells[("haiku", "hybrid_retrieval@v1")]
    assert base["success_rate"] == 0.25
    assert hyb["success_rate"] == 0.75
    assert base["mean_n_chunks"] == 0
    assert hyb["mean_n_chunks"] > 0
    # Skill counts: 6 chunk_ids over 4 hybrid rows -> 'regex' fires 4×, etc.
    assert agg["by_skill"]["regex"]["n_fires"] == 4
    assert "t1" in agg["by_skill"]["regex"]["by_task"]
    # Pairwise: hybrid_retrieval lifts haiku from 0.25 to 0.75 -> +0.50 delta.
    pw = {(r["model"], r["policy"]): r for r in agg["pairwise"]}
    assert ("haiku", "hybrid_retrieval@v1") in pw
    rec = pw[("haiku", "hybrid_retrieval@v1")]
    assert rec["delta"] == 0.5
    # CI should bracket the true delta in either direction (small n, so wide).
    assert rec["ci95_lo"] <= rec["delta"] <= rec["ci95_hi"]


def test_markdown_report_contains_expected_sections():
    agg = aggregate(_sample_rows())
    md = markdown_report(agg, title="Test")
    assert "# Test" in md
    assert "## Headline" in md
    assert "## Per-cell results" in md
    assert "## Skill coverage" in md
    assert "## Pairwise deltas" in md
    # Cells appear in the table.
    assert "hybrid_retrieval@v1" in md


def test_perf_vs_cost_chart_writes_png(tmp_path: Path):
    agg = aggregate(_sample_rows())
    out_png = tmp_path / "chart.png"
    perf_vs_cost_chart(agg, out_png)
    assert out_png.exists()
    assert out_png.stat().st_size > 0


def test_synthesize_then_build_report_smoke(tmp_path: Path):
    """End-to-end: synthesize a CSV, run build_report, check outputs exist."""
    csv_path = tmp_path / "fake.csv"
    md_path = tmp_path / "fake.report.md"
    png_path = tmp_path / "fake.png"

    synth_cmd = [
        sys.executable,
        str(REPO / "scripts" / "synthesize_sweep_csv.py"),
        "--out", str(csv_path),
        "--runs", "2",
    ]
    r1 = subprocess.run(synth_cmd, capture_output=True, text=True, check=False, cwd=REPO)
    assert r1.returncode == 0, r1.stderr
    assert csv_path.exists()

    build_cmd = [
        sys.executable,
        str(REPO / "scripts" / "build_report.py"),
        str(csv_path),
        "--out-md", str(md_path),
        "--out-png", str(png_path),
    ]
    r2 = subprocess.run(build_cmd, capture_output=True, text=True, check=False, cwd=REPO)
    assert r2.returncode == 0, r2.stderr
    assert md_path.exists() and md_path.stat().st_size > 0
    assert png_path.exists() and png_path.stat().st_size > 0
