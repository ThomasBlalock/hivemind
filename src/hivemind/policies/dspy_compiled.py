"""System 2 — DSPy-Compiled, Per-Model Skill Distillations.

Design: docs/context_injection/02_dspy_compiled_skills.md

This module ships **scaffolded**. The serve-time policy reads compiled
artifacts under ``models/dspy/<version>/``:

- ``distillations.jsonl``: per-(skill_id, model) compressed bodies.
- ``selector.json``: per-skill model-conditioned inclusion logits.
- ``order_prior.json``: per-skill position prior.

If no artifacts exist for the requested target model, this policy gracefully
degrades to System 1's behavior (raw bodies, rerank-threshold selection).

The training script lives at ``train.py`` and is only invoked offline against
the eval harness — see docs.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from hivemind.config import default_corpus_path, models_dir
from hivemind.corpus.ingest import load_jsonl
from hivemind.corpus.schema import Skill
from hivemind.policies.base import Chunk, SynthesizeRequest, SynthesizeResponse
from hivemind.policies.hybrid_retrieval import HybridRetrievalPolicy


class DSPyCompiledPolicy:
    name = "dspy_compiled@v1"

    def __init__(self, skills: list[Skill], artifacts_dir: Path | None = None):
        self._skills_by_id = {s.id: s for s in skills}
        self._base = HybridRetrievalPolicy(skills)
        self._artifacts_dir = artifacts_dir or (models_dir() / "dspy" / "v1")
        self._distillations: dict[tuple[str, str], str] = {}
        self._load_artifacts()

    def _load_artifacts(self) -> None:
        path = self._artifacts_dir / "distillations.jsonl"
        if not path.exists():
            return
        with path.open() as f:
            for line in f:
                row = json.loads(line)
                self._distillations[(row["skill_id"], row["model"])] = row["body"]

    def _distilled_body(self, skill_id: str, model: str) -> str | None:
        return self._distillations.get((skill_id, model))

    def synthesize(self, req: SynthesizeRequest) -> SynthesizeResponse:
        t0 = time.perf_counter()
        # Reuse System 1's retrieval + reranking; swap bodies for distilled versions
        # when available for the target model.
        base = self._base.synthesize(req)
        # Re-emit chunks, substituting distilled bodies and using the same packing.
        new_chunks: list[Chunk] = []
        total_tokens = 0
        for c in base.chunks:
            distilled = self._distilled_body(c.skill_id, req.model)
            if distilled is None:
                new_chunks.append(c)
                total_tokens += self._skills_by_id[c.skill_id].tokens
                continue
            from hivemind.tokenize import count_tokens
            new_chunks.append(
                Chunk(
                    content=distilled,
                    position=c.position,
                    skill_id=c.skill_id,
                    source_sha=c.source_sha,
                    score=c.score,
                )
            )
            total_tokens += count_tokens(distilled)

        latency_ms = int((time.perf_counter() - t0) * 1000)
        return SynthesizeResponse(
            chunks=new_chunks, policy=self.name, tokens=total_tokens, latency_ms=latency_ms
        )


def _factory():
    skills = load_jsonl(default_corpus_path())
    skills = [s for s in skills if s.audit_status == "passed"]
    return DSPyCompiledPolicy(skills)


def __register():
    from hivemind.policies.registry import register_policy
    register_policy("dspy_compiled", _factory)


__register()
