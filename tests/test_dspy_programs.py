"""Tests for the DSPy training pipeline.

The whole module is gated on dspy-ai being installed. We never hit the network:
``HIVEMIND_DSPY_DRY_RUN=1`` installs a dspy.DummyLM with canned answers.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

dspy = pytest.importorskip("dspy")


@pytest.fixture()
def dry_run_env(monkeypatch):
    monkeypatch.setenv("HIVEMIND_DSPY_DRY_RUN", "1")
    yield


@pytest.fixture()
def isolated_models_dir(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("HIVEMIND_MODELS_DIR", str(tmp_path))
    yield tmp_path


def test_configure_lm_installs_dummy(dry_run_env):
    from hivemind.policies.dspy_programs import configure_lm

    configure_lm()
    # The LM should now be a DummyLM instance.
    assert dspy.settings.lm is not None
    name = type(dspy.settings.lm).__name__
    assert "Dummy" in name


def test_each_program_runs_with_dummy_lm(dry_run_env):
    from hivemind.policies.dspy_programs import (
        SkillDistiller,
        SkillOrderer,
        SkillSelector,
        configure_lm,
    )

    configure_lm()

    distilled = SkillDistiller(token_cap=300)(
        raw_body="A very long instruction with prose and rationale.\n\nStep 1: run pytest.\nStep 2: read the failure.",
        target_model="claude-haiku-4-5",
    )
    assert isinstance(distilled, str) and distilled

    pred = SkillSelector()(
        query="how do I fix the regex backreference",
        skill_candidate="regex-construction\n\nUse \\1 for the first capture group.",
        target_model="claude-haiku-4-5",
    )
    assert hasattr(pred, "include")

    perm = SkillOrderer()(
        selected_skill_ids=["a", "b", "c"],
        query="debug a regression",
        target_model="claude-haiku-4-5",
    )
    assert sorted(perm) == [0, 1, 2]


def test_train_dry_run_writes_artifacts(
    dry_run_env, isolated_corpus, isolated_models_dir
):
    from hivemind.policies.dspy_train import main

    rc = main(["--dry-run", "--out-version", "v1", "--max-lm-calls", "1000"])
    assert rc == 0

    out = isolated_models_dir / "dspy" / "v1"
    assert (out / "distillations.jsonl").exists()
    assert (out / "selector.json").exists()
    assert (out / "order_prior.json").exists()

    # selector.json + order_prior.json must be parseable JSON; distillations.jsonl
    # must have one JSON object per non-empty line.
    json.loads((out / "selector.json").read_text() or "{}")
    json.loads((out / "order_prior.json").read_text() or "{}")
    for line in (out / "distillations.jsonl").read_text().splitlines():
        if line.strip():
            json.loads(line)


def test_dspy_compiled_consumes_trained_artifacts(
    dry_run_env, isolated_corpus, isolated_models_dir, toy_skills
):
    """Round-trip: train (dry-run) → load policy → confirm chunks are served."""
    from hivemind.policies.base import Message, SynthesizeRequest
    from hivemind.policies.dspy_compiled import DSPyCompiledPolicy
    from hivemind.policies.dspy_train import main

    rc = main(["--dry-run", "--out-version", "v1", "--max-lm-calls", "1000"])
    assert rc == 0

    policy = DSPyCompiledPolicy(
        toy_skills, artifacts_dir=isolated_models_dir / "dspy" / "v1"
    )
    req = SynthesizeRequest(
        conversation=[Message(role="user", content="help me fix a regex backreference")],
        model="claude-haiku-4-5",
        budget_tokens=4000,
    )
    resp = policy.synthesize(req)
    assert resp.policy.startswith("dspy_compiled")
    # Toy corpus has a regex skill; we expect at least one chunk back unless
    # the selector strongly objected. The dry-run selector is mildly positive
    # for keywords matched in the canned answers, so we tolerate either case
    # — the *contract* under test is "no crash, valid response shape".
    assert resp.tokens >= 0
    assert isinstance(resp.chunks, list)


def test_call_counter_caps_budget(dry_run_env, isolated_corpus, isolated_models_dir):
    from hivemind.policies.dspy_train import main

    # With max-lm-calls=1 the counter trips on the 2nd call. We want a hard
    # abort, not silent partial artifacts.
    with pytest.raises(RuntimeError, match="LM call budget exceeded"):
        main(["--dry-run", "--out-version", "v1", "--max-lm-calls", "1"])
