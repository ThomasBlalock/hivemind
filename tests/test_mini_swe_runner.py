"""Smoke tests for the mini-swe-agent integration.

Uses mini-swe-agent's bundled DeterministicModel — no API calls, no network.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from hivemind.harness.mini_swe_runner import TaskSpec, run_task


def _deterministic_model():
    from minisweagent.models.test_models import DeterministicModel, make_output

    # Two-step program: ls then submit. Doesn't fix anything, just exercises
    # the agent loop so we know the integration is wired correctly.
    return DeterministicModel(
        outputs=[
            make_output("THOUGHT: ls.", actions=[{"command": "ls"}], cost=0.001),
            make_output(
                "THOUGHT: done.",
                actions=[{"command": "echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT"}],
                cost=0.001,
            ),
        ]
    )


@pytest.fixture()
def fizzbuzz_task(tmp_path: Path) -> TaskSpec:
    """Copy the real fizzbuzz fixture into a tmp dir so the test runs in
    isolation and never edits files in the repo proper."""
    import shutil

    src = Path(__file__).resolve().parents[1] / "eval_tasks" / "fizzbuzz_off_by_one" / "repo"
    dest = tmp_path / "repo"
    shutil.copytree(src, dest)
    return TaskSpec(
        id="fizzbuzz_off_by_one",
        prompt="fix the fizzbuzz bug",
        work_dir=dest,
        test_cmd="pytest test_fizzbuzz.py -x -q",
    )


def test_run_task_baseline_a_no_chunks(fizzbuzz_task, isolated_corpus):
    """BaselineA injects no skills; agent loop must still complete."""
    r = run_task(fizzbuzz_task, model=_deterministic_model(), policy_name="baseline_a")
    assert r.n_chunks == 0
    assert r.n_calls >= 1
    # Deterministic model doesn't actually fix the bug → test fails → success=False.
    assert r.success is False


def test_run_task_hybrid_retrieval_injects_chunks(fizzbuzz_task, isolated_corpus):
    """System 1 should inject relevant chunks when the prompt overlaps a skill.

    Test the wiring with a prompt that mentions regex (a toy-corpus skill)
    explicitly — independent of stub-reranker calibration. A prompt that
    doesn't overlap the corpus is correctly handled by the threshold (we
    don't assert on it here)."""
    task = TaskSpec(
        id="fizzbuzz_off_by_one",
        prompt="debug a python regex traceback and bisect the regression",
        work_dir=fizzbuzz_task.work_dir,
        test_cmd=fizzbuzz_task.test_cmd,
    )
    r = run_task(task, model=_deterministic_model(), policy_name="hybrid_retrieval")
    assert r.policy.startswith("hybrid_retrieval")
    assert r.n_chunks >= 1
    assert any(cid in {"python-debugging", "regex-construction", "git-bisect"} for cid in r.chunk_ids)


def test_run_task_records_cost(fizzbuzz_task, isolated_corpus):
    r = run_task(fizzbuzz_task, model=_deterministic_model(), policy_name="baseline_a")
    # Each fake call reports cost=0.001 — two calls expected.
    assert r.cost_usd > 0
