"""Latency budget asserts. Offline (stub backends) — only verifies the wiring
adds no surprise overhead. Real-backend latency must be measured separately
against the live service (see docs/serving/README.md)."""

from __future__ import annotations

import time

from hivemind.policies.base import Message, SynthesizeRequest
from hivemind.policies.hybrid_retrieval import HybridRetrievalPolicy


def test_hybrid_retrieval_under_200ms_offline(toy_skills):
    p = HybridRetrievalPolicy(toy_skills)
    # Warm up the embedder + bm25 caches.
    req = SynthesizeRequest(
        conversation=[Message(role="user", content="bisect regression")],
        model="test",
        budget_tokens=2000,
    )
    p.synthesize(req)

    timings = []
    for _ in range(20):
        t0 = time.perf_counter()
        p.synthesize(req)
        timings.append((time.perf_counter() - t0) * 1000)
    timings.sort()
    p50 = timings[len(timings) // 2]
    p95 = timings[int(len(timings) * 0.95)]
    # Offline: cache hits should be near-zero. Plenty of headroom under the
    # 200ms p50 production budget. Generous limit to avoid flakes on slow CI.
    assert p50 < 100, f"p50={p50:.1f}ms exceeds 100ms (offline cache-hit budget)"
    assert p95 < 200, f"p95={p95:.1f}ms exceeds 200ms"
