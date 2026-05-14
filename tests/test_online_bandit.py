from __future__ import annotations

from hivemind.policies.base import Message, SynthesizeRequest
from hivemind.policies.online_bandit import OnlineBanditPolicy


def _req(text: str, traj: str | None = None) -> SynthesizeRequest:
    return SynthesizeRequest(
        conversation=[Message(role="user", content=text)],
        model="test",
        budget_tokens=4000,
        trajectory_id=traj,
        turn_index=0,
    )


def test_feedback_updates_only_pulled_arms(toy_skills):
    p = OnlineBanditPolicy(toy_skills)
    resp = p.synthesize(_req("bisect this regression", traj="t-1"))
    n = p.record_feedback("t-1", success=True, cost_usd=0.0)
    # n equals the number of arms touched, which equals the number of chunks served.
    assert n == len(resp.chunks)


def test_feedback_unknown_trajectory_returns_zero(toy_skills):
    p = OnlineBanditPolicy(toy_skills)
    assert p.record_feedback("nope", success=True, cost_usd=0.0) == 0


def test_save_state_writes_file(toy_skills, tmp_path):
    p = OnlineBanditPolicy(toy_skills, state_dir=tmp_path)
    p.synthesize(_req("regex pattern", traj="t-2"))
    p.record_feedback("t-2", success=True, cost_usd=0.01)
    out = p.save_state()
    assert out.exists()
