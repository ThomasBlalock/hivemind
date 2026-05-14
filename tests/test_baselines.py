from __future__ import annotations

from hivemind.policies.base import Message, SynthesizeRequest
from hivemind.policies.baseline import BaselineA, BaselineB


def _req(text: str, budget: int = 4000) -> SynthesizeRequest:
    return SynthesizeRequest(
        conversation=[Message(role="user", content=text)],
        model="test",
        budget_tokens=budget,
    )


def test_baseline_a_injects_nothing(toy_skills):
    r = BaselineA().synthesize(_req("anything"))
    assert r.chunks == []
    assert r.tokens == 0


def test_baseline_b_fires_on_keyword(toy_skills):
    r = BaselineB(toy_skills).synthesize(_req("I need to bisect this regression"))
    ids = {c.skill_id for c in r.chunks}
    assert "git-bisect" in ids


def test_baseline_b_silent_on_unrelated(toy_skills):
    r = BaselineB(toy_skills).synthesize(_req("what's the weather like in tokyo"))
    assert r.chunks == []


def test_baseline_b_ignores_budget(toy_skills):
    """Baseline B's defining flaw: no budget check. Encoded so we notice if someone 'fixes' it."""
    r = BaselineB(toy_skills).synthesize(_req("bisect traceback regex", budget=10))
    assert r.tokens > 10  # would have skipped under a budget-respecting policy
