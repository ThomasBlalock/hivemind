from __future__ import annotations

from hivemind.policies.base import Message, SynthesizeRequest
from hivemind.policies.hybrid_retrieval import HybridRetrievalPolicy, _build_query


def _req(text: str, budget: int = 4000) -> SynthesizeRequest:
    return SynthesizeRequest(
        conversation=[Message(role="user", content=text)],
        model="test",
        budget_tokens=budget,
    )


def test_query_uses_last_n_turns():
    msgs = [
        Message(role="user", content="we have a regression"),
        Message(role="assistant", content="ok"),
        Message(role="user", content="please bisect it"),
    ]
    q = _build_query(msgs, window=3)
    assert "bisect" in q.lower()
    assert "regression" in q.lower()


def test_paraphrase_retrieves_skill(toy_skills):
    p = HybridRetrievalPolicy(toy_skills)
    # No literal "bisect" keyword but semantically related — should still rank highly
    # on BM25 via "regression" + "find when broke" trigger overlap.
    r = p.synthesize(_req("when did this regression start, find the broken commit"))
    ids = [c.skill_id for c in r.chunks]
    assert "git-bisect" in ids


def test_budget_packing_respects_limit(toy_skills):
    p = HybridRetrievalPolicy(toy_skills, rerank_threshold=0.0)
    r = p.synthesize(_req("traceback regex bisect", budget=50))
    # With a tight 50-token budget and 10% headroom, no toy skill fits.
    assert r.tokens <= 50


def test_empty_query_returns_no_chunks(toy_skills):
    p = HybridRetrievalPolicy(toy_skills)
    req = SynthesizeRequest(conversation=[], model="test", budget_tokens=4000)
    r = p.synthesize(req)
    assert r.chunks == []


def test_chunks_carry_score_and_skill_id(toy_skills):
    p = HybridRetrievalPolicy(toy_skills)
    r = p.synthesize(_req("debug a python traceback please"))
    if r.chunks:
        for c in r.chunks:
            assert c.skill_id
            assert c.score is not None
