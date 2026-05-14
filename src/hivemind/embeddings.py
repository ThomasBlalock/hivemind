"""Embedding backends.

Default is a deterministic stub (no network). Set HIVEMIND_EMBEDDER=voyage and
VOYAGE_API_KEY to use the real backend.
"""

from __future__ import annotations

import hashlib
import os
from typing import Protocol

import numpy as np


class Embedder(Protocol):
    dim: int
    name: str

    def embed(self, texts: list[str]) -> np.ndarray:
        """Return shape (n, dim) float32 array."""
        ...


class StubEmbedder:
    """Deterministic hash-based embedding. No network. Bad at semantics, fine for tests.

    Splits each text into tokens, hashes each into a bucket, and produces a
    sparse-bag-of-words style dense vector. Cosine similarity between two stub
    vectors is just lexical overlap — good enough to validate plumbing, useless
    for actual retrieval quality. Live mode uses :class:`VoyageEmbedder`.
    """

    dim = 256
    name = "stub-256"

    def embed(self, texts: list[str]) -> np.ndarray:
        out = np.zeros((len(texts), self.dim), dtype=np.float32)
        for i, t in enumerate(texts):
            for tok in t.lower().split():
                h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
                out[i, h % self.dim] += 1.0
            n = np.linalg.norm(out[i])
            if n > 0:
                out[i] /= n
        return out


class VoyageEmbedder:
    """Real voyage-3 backend. Requires `voyageai` and VOYAGE_API_KEY."""

    dim = 1024
    name = "voyage-3"

    def __init__(self, model: str = "voyage-3"):
        import voyageai  # type: ignore
        self._client = voyageai.Client()
        self._model = model

    def embed(self, texts: list[str]) -> np.ndarray:
        result = self._client.embed(texts, model=self._model, input_type="document")
        return np.asarray(result.embeddings, dtype=np.float32)


def get_embedder() -> Embedder:
    """Pick a backend based on env. Falls back to stub if voyage isn't installed."""
    backend = os.environ.get("HIVEMIND_EMBEDDER", "stub").lower()
    if backend == "voyage":
        try:
            return VoyageEmbedder()
        except Exception as e:  # noqa: BLE001
            import warnings
            warnings.warn(f"VoyageEmbedder unavailable ({e}); falling back to stub", stacklevel=2)
    return StubEmbedder()
