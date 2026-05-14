"""Baseline injection policies.

- BaselineA: inject nothing. The "no skills" lower bound.
- BaselineB: naive keyword trigger over the last user message. The current
  state-of-practice. See docs/context_injection/README.md.
"""

from __future__ import annotations

import time

from hivemind.corpus.schema import Skill
from hivemind.policies.base import Chunk, SynthesizeRequest, SynthesizeResponse


class BaselineA:
    """No injection."""

    name = "baseline_a@v1"

    def synthesize(self, req: SynthesizeRequest) -> SynthesizeResponse:
        return SynthesizeResponse(chunks=[], policy=self.name, tokens=0, latency_ms=0)


class BaselineB:
    """Naive keyword trigger over the last user message.

    A skill fires if any of its `triggers` appears as a substring in the last
    user message (case-insensitive). Order: corpus order. No budget check —
    this reproduces the failure mode CLAUDE.md is reacting to.
    """

    name = "baseline_b@v1"

    def __init__(self, skills: list[Skill]):
        self._skills = skills

    def _last_user(self, req: SynthesizeRequest) -> str:
        for m in reversed(req.conversation):
            if m.role == "user":
                return m.content.lower()
        return ""

    def synthesize(self, req: SynthesizeRequest) -> SynthesizeResponse:
        t0 = time.perf_counter()
        text = self._last_user(req)
        chunks: list[Chunk] = []
        total_tokens = 0
        for s in self._skills:
            if any(trig.lower() in text for trig in s.triggers):
                chunks.append(
                    Chunk(
                        content=s.body,
                        position="system_suffix",
                        skill_id=s.id,
                        source_sha=s.source,
                    )
                )
                total_tokens += s.tokens
        latency_ms = int((time.perf_counter() - t0) * 1000)
        return SynthesizeResponse(chunks=chunks, policy=self.name, tokens=total_tokens, latency_ms=latency_ms)


def _factory_a():
    return BaselineA()


def _factory_b():
    from hivemind.config import default_corpus_path
    from hivemind.corpus.ingest import load_jsonl

    skills = load_jsonl(default_corpus_path())
    skills = [s for s in skills if s.audit_status == "passed"]
    return BaselineB(skills)


def __register():
    from hivemind.policies.registry import register_policy
    register_policy("baseline_a", _factory_a)
    register_policy("baseline_b", _factory_b)


__register()
