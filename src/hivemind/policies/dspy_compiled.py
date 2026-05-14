"""System 2 — DSPy-Compiled, Per-Model Skill Distillations.

Design: docs/context_injection/02_dspy_compiled_skills.md

Loads three artifacts from ``models/dspy/<version>/`` written by
``dspy_train.py``:

- ``distillations.jsonl`` — per-(skill_id, model) compressed bodies.
- ``selector.json``       — per-skill, per-model inclusion logits.
- ``order_prior.json``    — per-skill, per-model position prior (higher → earlier).

If artifacts are missing or empty, this policy gracefully degrades to System
1: raw bodies, rerank-threshold selection, retrieval order.

The serve-time module does **not** import ``dspy``; that dependency is only
needed by the offline trainer.
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
from hivemind.tokenize import count_tokens

# Logit threshold: positive logits mean "selector agreed the skill helps."
# Zero means no evidence either way → fall back to retrieval-driven gating.
SELECTOR_LOGIT_THRESHOLD = 0.0


class DSPyCompiledPolicy:
    name = "dspy_compiled@v1"

    def __init__(self, skills: list[Skill], artifacts_dir: Path | None = None):
        self._skills_by_id = {s.id: s for s in skills}
        self._base = HybridRetrievalPolicy(skills)
        self._artifacts_dir = artifacts_dir or (models_dir() / "dspy" / "v1")
        self._distillations: dict[tuple[str, str], str] = {}
        # selector[(skill_id, model)] = logit
        self._selector: dict[tuple[str, str], float] = {}
        # order_prior[(skill_id, model)] = float in [0,1] (higher = earlier)
        self._order_prior: dict[tuple[str, str], float] = {}
        self._load_artifacts()

    # --- loading ---------------------------------------------------------

    def _load_artifacts(self) -> None:
        self._load_distillations()
        self._load_selector()
        self._load_order_prior()

    def _load_distillations(self) -> None:
        path = self._artifacts_dir / "distillations.jsonl"
        if not path.exists():
            return
        with path.open() as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                self._distillations[(row["skill_id"], row["model"])] = row["body"]

    def _load_selector(self) -> None:
        path = self._artifacts_dir / "selector.json"
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text() or "{}")
        except json.JSONDecodeError:
            return
        for skill_id, per_model in data.items():
            for model, payload in per_model.items():
                logit = float(payload.get("logit", 0.0)) if isinstance(payload, dict) else float(payload)
                self._selector[(skill_id, model)] = logit

    def _load_order_prior(self) -> None:
        path = self._artifacts_dir / "order_prior.json"
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text() or "{}")
        except json.JSONDecodeError:
            return
        for skill_id, per_model in data.items():
            for model, val in per_model.items():
                self._order_prior[(skill_id, model)] = float(val)

    # --- per-(skill,model) lookups --------------------------------------

    def _distilled_body(self, skill_id: str, model: str) -> str | None:
        return self._distillations.get((skill_id, model))

    def _selector_logit(self, skill_id: str, model: str) -> float | None:
        return self._selector.get((skill_id, model))

    def _order_bonus(self, skill_id: str, model: str) -> float:
        return self._order_prior.get((skill_id, model), 0.0)

    # --- core ------------------------------------------------------------

    def synthesize(self, req: SynthesizeRequest) -> SynthesizeResponse:
        t0 = time.perf_counter()
        # System 1 produces an initial ranked list; we filter + reorder + swap bodies.
        base = self._base.synthesize(req)

        # Apply learned selector: drop chunks whose (skill, model) logit is
        # strongly negative. Absence of a learned entry is "no opinion" — keep.
        filtered: list[Chunk] = []
        for c in base.chunks:
            logit = self._selector_logit(c.skill_id, req.model)
            if logit is not None and logit < SELECTOR_LOGIT_THRESHOLD:
                continue
            filtered.append(c)

        # Apply order prior to tiebreak the System-1 rerank score. The bonus is
        # additive on top of the existing score, so System 1 still drives the
        # bulk of the ordering — we only nudge.
        def _sort_key(c: Chunk) -> float:
            base_score = c.score if c.score is not None else 0.0
            return -(base_score + 0.05 * self._order_bonus(c.skill_id, req.model))

        filtered.sort(key=_sort_key)

        # Substitute distilled bodies where available; recompute tokens accordingly.
        new_chunks: list[Chunk] = []
        total_tokens = 0
        for c in filtered:
            distilled = self._distilled_body(c.skill_id, req.model)
            if distilled is None:
                new_chunks.append(c)
                total_tokens += self._skills_by_id[c.skill_id].tokens
                continue
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
