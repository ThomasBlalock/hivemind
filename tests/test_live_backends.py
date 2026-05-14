"""Live-backend smoke tests — skipped unless API keys are present.

These don't run on default CI. Enable by setting VOYAGE_API_KEY locally and
running:
    pytest tests/test_live_backends.py
"""

from __future__ import annotations

import os

import pytest


@pytest.mark.skipif(not os.environ.get("VOYAGE_API_KEY"), reason="no VOYAGE_API_KEY")
def test_voyage_embedder_returns_real_vectors():
    from hivemind.embeddings import VoyageEmbedder

    e = VoyageEmbedder()
    vecs = e.embed(["debug a python traceback"])
    assert vecs.shape == (1, e.dim)
    assert (vecs != 0).any()


@pytest.mark.skipif(not os.environ.get("VOYAGE_API_KEY"), reason="no VOYAGE_API_KEY")
def test_voyage_reranker_returns_scores():
    from hivemind.reranker import VoyageReranker

    r = VoyageReranker()
    scores = r.rerank(
        query="bisect a git regression",
        candidates=["git bisect playbook ...", "regex construction ..."],
    )
    assert len(scores) == 2
    assert scores[0] > scores[1]  # the bisect doc should rank higher
