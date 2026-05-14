"""Build retrieval indexes over the skill corpus.

Two indexes:
- Dense: embeddings of `title + description + body[:200_tokens]`.
- Sparse: BM25 over `title + description + triggers + body`.

For the offline/stubbed default, both indexes live in memory and are rebuilt
on policy load. Replace with LanceDB + persisted BM25 once we scale beyond the
toy corpus.

See docs/context_injection/01_hybrid_retrieval.md.
"""

from __future__ import annotations

from dataclasses import dataclass

import bm25s
import numpy as np

from hivemind.corpus.schema import Skill
from hivemind.embeddings import Embedder, get_embedder
from hivemind.tokenize import count_tokens


def _dense_doc_text(s: Skill, body_token_cap: int = 200) -> str:
    """Body is truncated by tokens to keep the embedding focused."""
    body = s.body
    if count_tokens(body) > body_token_cap:
        # Rough character-based truncation. Cheap; tokens != chars but close enough
        # for "first ~200 tokens of body" and we don't need to round-trip the encoder.
        body = body[: body_token_cap * 4]
    return f"{s.title}\n{s.description}\n{body}"


def _sparse_doc_text(s: Skill) -> str:
    triggers = " ".join(s.triggers)
    return f"{s.title} {s.description} {triggers} {s.body}"


@dataclass
class HybridIndex:
    skills: list[Skill]
    dense_vectors: np.ndarray  # (n, dim)
    bm25: bm25s.BM25
    embedder_name: str

    @classmethod
    def build(cls, skills: list[Skill], embedder: Embedder | None = None) -> "HybridIndex":
        embedder = embedder or get_embedder()
        dense_texts = [_dense_doc_text(s) for s in skills]
        vectors = embedder.embed(dense_texts) if skills else np.zeros((0, embedder.dim), dtype=np.float32)

        sparse_corpus = [_sparse_doc_text(s) for s in skills]
        tokens = bm25s.tokenize(sparse_corpus, stopwords="en")
        bm25 = bm25s.BM25()
        bm25.index(tokens)

        return cls(skills=skills, dense_vectors=vectors, bm25=bm25, embedder_name=embedder.name)

    def dense_search(self, query_vec: np.ndarray, k: int) -> list[tuple[int, float]]:
        if len(self.skills) == 0:
            return []
        scores = self.dense_vectors @ query_vec
        k = min(k, len(self.skills))
        top = np.argpartition(-scores, k - 1)[:k]
        # Sort the top-k by score descending for stable downstream merging.
        top = top[np.argsort(-scores[top])]
        return [(int(i), float(scores[i])) for i in top]

    def sparse_search(self, query: str, k: int) -> list[tuple[int, float]]:
        if len(self.skills) == 0:
            return []
        q_tokens = bm25s.tokenize([query], stopwords="en")
        k = min(k, len(self.skills))
        results, scores = self.bm25.retrieve(q_tokens, k=k)
        # results is shape (1, k), scores is (1, k)
        return [(int(results[0][i]), float(scores[0][i])) for i in range(k)]
