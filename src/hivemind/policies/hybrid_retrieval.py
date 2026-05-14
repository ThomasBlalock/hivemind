"""System 1 — Hybrid Retrieval with Reranking.

Design: docs/context_injection/01_hybrid_retrieval.md

Pipeline:
  conversation -> query construction -> {dense, sparse} retrieval ->
    RRF merge -> cross-encoder rerank -> threshold + greedy-pack under budget ->
    chunks.
"""

from __future__ import annotations

import hashlib
import time
from collections import OrderedDict

import numpy as np

from hivemind.corpus.index import HybridIndex
from hivemind.corpus.schema import Skill
from hivemind.embeddings import Embedder, get_embedder
from hivemind.policies.base import Chunk, Message, SynthesizeRequest, SynthesizeResponse
from hivemind.reranker import Reranker, get_reranker

# Tunables. See ablations in the design doc.
QUERY_TURN_WINDOW = 3
K_DENSE = 40
K_SPARSE = 40
K_CANDIDATES = 20
RERANK_THRESHOLD = 0.30
BUDGET_HEADROOM = 0.10  # reserve 10% of budget for tokenizer drift
CACHE_SIZE = 10_000


def _build_query(conversation: list[Message], window: int = QUERY_TURN_WINDOW) -> str:
    """Last N turns + last assistant's tool-call names."""
    turns = []
    for m in conversation[-window:]:
        if m.role in ("user", "assistant"):
            turns.append(m.content)
    # Pull tool-call names from the most recent assistant turn, if any.
    tool_names: list[str] = []
    for m in reversed(conversation):
        if m.role == "assistant" and m.tool_calls:
            for tc in m.tool_calls:
                name = tc.get("name") or tc.get("function", {}).get("name")
                if name:
                    tool_names.append(name)
            break
    if tool_names:
        turns.append("tool calls in flight: " + ", ".join(tool_names))
    return "\n".join(turns).strip()


def _rrf_merge(
    rankings: list[list[tuple[int, float]]],
    k_const: int = 60,
) -> list[tuple[int, float]]:
    """Reciprocal Rank Fusion. Robust default for hybrid retrieval."""
    fused: dict[int, float] = {}
    for ranking in rankings:
        for rank, (idx, _score) in enumerate(ranking):
            fused[idx] = fused.get(idx, 0.0) + 1.0 / (k_const + rank + 1)
    return sorted(fused.items(), key=lambda kv: -kv[1])


class _LRUCache:
    def __init__(self, max_size: int):
        self._max = max_size
        self._data: OrderedDict = OrderedDict()

    def get(self, key):
        if key in self._data:
            self._data.move_to_end(key)
            return self._data[key]
        return None

    def put(self, key, value) -> None:
        self._data[key] = value
        self._data.move_to_end(key)
        if len(self._data) > self._max:
            self._data.popitem(last=False)


class HybridRetrievalPolicy:
    """System 1 implementation. Thread-unsafe; instantiate per worker."""

    name = "hybrid_retrieval@v1"

    def __init__(
        self,
        skills: list[Skill],
        embedder: Embedder | None = None,
        reranker: Reranker | None = None,
        index: HybridIndex | None = None,
        rerank_threshold: float | None = None,
    ):
        self._skills = skills
        self._embedder = embedder or get_embedder()
        self._reranker = reranker or get_reranker()
        self._index = index or HybridIndex.build(skills, embedder=self._embedder)
        # Threshold defaults to the reranker's own calibration. Overridable per instance.
        self._threshold = (
            rerank_threshold
            if rerank_threshold is not None
            else getattr(self._reranker, "default_threshold", RERANK_THRESHOLD)
        )
        self._cache: _LRUCache = _LRUCache(CACHE_SIZE)

    # --- pipeline stages -------------------------------------------------

    def _retrieve_candidates(self, query: str) -> list[int]:
        cache_key = ("cand", hashlib.md5(query.encode()).hexdigest())
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        q_vec = self._embedder.embed([query])[0]
        dense = self._index.dense_search(q_vec, K_DENSE)
        sparse = self._index.sparse_search(query, K_SPARSE)
        fused = _rrf_merge([dense, sparse])
        candidates = [idx for idx, _ in fused[:K_CANDIDATES]]
        self._cache.put(cache_key, candidates)
        return candidates

    def _rerank(self, query: str, candidate_indices: list[int]) -> list[tuple[int, float]]:
        if not candidate_indices:
            return []
        bodies = [self._skills[i].body for i in candidate_indices]
        scores = self._reranker.rerank(query, bodies)
        out = list(zip(candidate_indices, scores, strict=True))
        return sorted(out, key=lambda x: -x[1])

    def _pack(self, ranked: list[tuple[int, float]], budget_tokens: int) -> list[tuple[int, float]]:
        effective = int(budget_tokens * (1.0 - BUDGET_HEADROOM))
        selected = []
        used = 0
        for idx, score in ranked:
            if score < self._threshold:
                break
            s = self._skills[idx]
            if used + s.tokens > effective:
                continue
            selected.append((idx, score))
            used += s.tokens
        return selected

    # --- public api ------------------------------------------------------

    def synthesize(self, req: SynthesizeRequest) -> SynthesizeResponse:
        t0 = time.perf_counter()
        query = _build_query(req.conversation)
        if not query:
            return SynthesizeResponse(chunks=[], policy=self.name, tokens=0, latency_ms=0)

        candidates = self._retrieve_candidates(query)
        ranked = self._rerank(query, candidates)
        selected = self._pack(ranked, req.budget_tokens)

        chunks = []
        total_tokens = 0
        for idx, score in selected:
            s = self._skills[idx]
            chunks.append(
                Chunk(
                    content=s.body,
                    position="system_suffix",
                    skill_id=s.id,
                    source_sha=s.source,
                    score=score,
                )
            )
            total_tokens += s.tokens

        latency_ms = int((time.perf_counter() - t0) * 1000)
        return SynthesizeResponse(
            chunks=chunks, policy=self.name, tokens=total_tokens, latency_ms=latency_ms
        )


# Convenience for the registry.
def _factory_from_default_corpus():
    from hivemind.corpus.ingest import load_jsonl
    from hivemind.config import default_corpus_path

    skills = load_jsonl(default_corpus_path())
    # Only serve audit-passed skills. Manual-review ones are excluded until
    # a human signs off; failed ones never made it into the jsonl.
    skills = [s for s in skills if s.audit_status == "passed"]
    return HybridRetrievalPolicy(skills)


def __register():
    from hivemind.policies.registry import register_policy
    register_policy("hybrid_retrieval", _factory_from_default_corpus)


__register()
