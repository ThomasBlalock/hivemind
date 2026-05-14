from __future__ import annotations

from fastapi.testclient import TestClient


def _client(isolated_corpus):
    from hivemind.api.app import app
    return TestClient(app)


def test_healthz(isolated_corpus):
    c = _client(isolated_corpus)
    r = c.get("/healthz")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_policies_lists_all(isolated_corpus):
    c = _client(isolated_corpus)
    r = c.get("/policies").json()
    assert set(r["available"]) >= {"baseline_a", "baseline_b", "hybrid_retrieval", "dspy_compiled", "online_bandit"}


def test_synthesize_default_policy(isolated_corpus):
    c = _client(isolated_corpus)
    r = c.post("/synthesize", json={
        "conversation": [{"role": "user", "content": "help me bisect a regression"}],
        "model": "claude-sonnet-4-6",
        "budget_tokens": 2000,
        "harness": "test",
    })
    assert r.status_code == 200
    data = r.json()
    assert data["policy"].startswith("hybrid_retrieval")
    assert any(c["skill_id"] == "git-bisect" for c in data["chunks"])


def test_synthesize_unknown_policy_404(isolated_corpus):
    c = _client(isolated_corpus)
    r = c.post("/synthesize?policy=does_not_exist", json={
        "conversation": [{"role": "user", "content": "x"}],
        "model": "test",
        "budget_tokens": 100,
    })
    assert r.status_code == 404


def test_feedback_endpoint_accepts(isolated_corpus):
    c = _client(isolated_corpus)
    # Prime the online_bandit policy with a synthesize call.
    c.post("/synthesize?policy=online_bandit", json={
        "conversation": [{"role": "user", "content": "bisect"}],
        "model": "test",
        "budget_tokens": 4000,
        "trajectory_id": "traj-1",
    })
    r = c.post("/feedback", json={
        "trajectory_id": "traj-1", "success": True, "cost_usd": 0.05, "turns": 3,
    })
    assert r.status_code == 200
    assert r.json()["accepted"] is True
