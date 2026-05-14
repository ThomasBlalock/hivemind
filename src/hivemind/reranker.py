"""Cross-encoder reranker backends.

Default is a deterministic stub. Set HIVEMIND_RERANKER=voyage or cohere with
the matching API key to use a real backend.
"""

from __future__ import annotations

import hashlib
import os
from typing import Protocol


class Reranker(Protocol):
    name: str

    def rerank(self, query: str, candidates: list[str]) -> list[float]:
        """Return per-candidate score in [0, 1]; higher = more relevant."""
        ...


class StubReranker:
    """Token-overlap Jaccard. Cheap, deterministic, useful for tests only."""

    name = "stub-jaccard"
    default_threshold = 0.02  # Jaccard between short queries and long bodies is small.

    def rerank(self, query: str, candidates: list[str]) -> list[float]:
        q = set(query.lower().split())
        if not q:
            return [0.0] * len(candidates)
        scores = []
        for c in candidates:
            cs = set(c.lower().split())
            if not cs:
                scores.append(0.0)
                continue
            inter = len(q & cs)
            union = len(q | cs)
            # Add a tiny tie-breaker derived from the candidate hash so order is stable.
            tb = int(hashlib.md5(c.encode()).hexdigest()[:4], 16) / 0xFFFF * 1e-6
            scores.append(inter / union + tb if union else 0.0)
        return scores


class VoyageReranker:
    """Real voyage rerank-2 backend."""

    name = "voyage-rerank-2"
    default_threshold = 0.30  # calibrated starting point; tune after Phase 4 baselines.

    def __init__(self, model: str = "rerank-2"):
        import voyageai  # type: ignore
        self._client = voyageai.Client()
        self._model = model

    def rerank(self, query: str, candidates: list[str]) -> list[float]:
        if not candidates:
            return []
        result = self._client.rerank(query=query, documents=candidates, model=self._model)
        scored = sorted(result.results, key=lambda r: r.index)
        return [r.relevance_score for r in scored]


def get_reranker() -> Reranker:
    backend = os.environ.get("HIVEMIND_RERANKER", "stub").lower()
    if backend == "voyage":
        try:
            return VoyageReranker()
        except Exception as e:  # noqa: BLE001
            import warnings
            warnings.warn(f"VoyageReranker unavailable ({e}); falling back to stub", stacklevel=2)
    return StubReranker()
