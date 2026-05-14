"""DSPy programs for System 2 — distillation, selection, ordering.

This module is the **training-time** counterpart of ``dspy_compiled.py``. The
serve-time policy never imports this file; only ``dspy_train.py`` does. That
keeps the dspy-ai dependency optional for the API server.

Design: docs/context_injection/02_dspy_compiled_skills.md

Three programs:

- :class:`SkillDistiller` — rephrases a raw skill body for a specific target
  model, preserving actionable instructions and dropping human-only prose.
- :class:`SkillSelector` — predicate over (query, skill) deciding whether to
  inject. Returns ``include`` (bool) and a confidence in [0, 1].
- :class:`SkillOrderer` — re-permutes a selected set so attention-sensitive
  models see the most useful skill first.
"""

from __future__ import annotations

import os

try:
    import dspy
except ImportError as e:  # pragma: no cover
    raise RuntimeError(
        "dspy-ai not installed. Install with: pip install -e '.[dspy]'"
    ) from e


# --- signatures ------------------------------------------------------------


class DistillSignature(dspy.Signature):
    """Compress a skill body for a target model.

    Preserve every actionable instruction (commands, steps, hard rules, code
    snippets). Drop motivational prose, anecdotes, hedging, or anything that
    only helps a human reader. Keep the result under the requested token cap.
    Output ONLY the distilled body — no explanation, no preamble.
    """

    raw_skill: str = dspy.InputField(desc="Raw skill body as authored.")
    target_model: str = dspy.InputField(desc="Canonical model id, e.g. claude-haiku-4-5.")
    token_cap: int = dspy.InputField(desc="Upper bound for distilled body, in tokens.")
    distilled_skill: str = dspy.OutputField(desc="Compressed body, preserving all actionable instructions.")


class SelectSignature(dspy.Signature):
    """Decide whether a candidate skill helps the current query.

    Rubric: include the skill only if applying it would change the agent's
    output on this query in a way that increases task success. Vague topical
    relevance is not enough. Output ``include`` and ``confidence`` in [0,1].
    """

    query: str = dspy.InputField(desc="Last user turn(s) + last assistant tool calls.")
    skill_candidate: str = dspy.InputField(desc="Skill title + first 400 chars of body.")
    target_model: str = dspy.InputField(desc="Canonical model id.")
    include: bool = dspy.OutputField(desc="True iff this skill should be injected.")
    confidence: float = dspy.OutputField(desc="In [0,1].")


class OrderSignature(dspy.Signature):
    """Permute selected skill ids so the most useful one appears first.

    Attention is biased toward the start and end of long contexts. Order by
    expected impact on this query, not corpus order or title alphabetical
    order. Output a permutation of the input indices as integers.
    """

    skill_ids: list[str] = dspy.InputField(desc="Selected skill ids, in arbitrary order.")
    query: str = dspy.InputField(desc="Same query used for selection.")
    target_model: str = dspy.InputField(desc="Canonical model id.")
    permutation: list[int] = dspy.OutputField(
        desc="Indices into skill_ids in the new order, e.g. [2,0,1]."
    )


# --- modules ---------------------------------------------------------------


# Default token cap for distillations. Big enough to keep meaningful skills,
# small enough to put pressure on the compressor.
DEFAULT_TOKEN_CAP = 400


class SkillDistiller(dspy.Module):
    def __init__(self, token_cap: int = DEFAULT_TOKEN_CAP):
        super().__init__()
        self._cap = token_cap
        self._program = dspy.ChainOfThought(DistillSignature)

    def forward(self, raw_body: str, target_model: str) -> str:
        result = self._program(
            raw_skill=raw_body, target_model=target_model, token_cap=self._cap
        )
        return getattr(result, "distilled_skill", raw_body) or raw_body


class SkillSelector(dspy.Module):
    def __init__(self):
        super().__init__()
        self._program = dspy.ChainOfThought(SelectSignature)

    def forward(self, query: str, skill_candidate: str, target_model: str):
        return self._program(
            query=query, skill_candidate=skill_candidate, target_model=target_model
        )


class SkillOrderer(dspy.Module):
    def __init__(self):
        super().__init__()
        self._program = dspy.ChainOfThought(OrderSignature)

    def forward(self, selected_skill_ids: list[str], query: str, target_model: str) -> list[int]:
        result = self._program(
            skill_ids=selected_skill_ids, query=query, target_model=target_model
        )
        perm = getattr(result, "permutation", None)
        # Sanitize: keep only in-range, deduplicated indices; fall back to
        # identity if the LM produced garbage.
        if not isinstance(perm, list):
            return list(range(len(selected_skill_ids)))
        seen: set[int] = set()
        cleaned: list[int] = []
        for x in perm:
            try:
                i = int(x)
            except (TypeError, ValueError):
                continue
            if 0 <= i < len(selected_skill_ids) and i not in seen:
                seen.add(i)
                cleaned.append(i)
        # Append any unseen indices to keep the permutation total.
        for i in range(len(selected_skill_ids)):
            if i not in seen:
                cleaned.append(i)
        return cleaned


# --- LM configuration ------------------------------------------------------


def configure_lm() -> None:
    """Wire up an LM in ``dspy.settings``.

    Reads ``HIVEMIND_DSPY_LM`` (a litellm model id, e.g.
    ``openrouter/anthropic/claude-haiku-4-5``). When ``HIVEMIND_DSPY_DRY_RUN=1``
    is set, installs a :class:`dspy.DummyLM` with canned answers so tests and
    the ``--dry-run`` trainer never touch the network.
    """
    if os.environ.get("HIVEMIND_DSPY_DRY_RUN") == "1":
        # Cycled canned answers; covers all three signatures' OutputFields.
        # DummyLM tolerates extra/missing keys; signature adapter picks what fits.
        canned = [
            {
                "reasoning": "compressing without losing commands",
                "distilled_skill": "step 1: run command. step 2: verify output.",
                "include": True,
                "confidence": 0.8,
                "permutation": [0],
            },
            {
                "reasoning": "noisy match; better to skip",
                "distilled_skill": "command: run pytest -k regex",
                "include": False,
                "confidence": 0.2,
                "permutation": [0, 1],
            },
            {
                "reasoning": "strongest first",
                "distilled_skill": "step: bisect to find regression",
                "include": True,
                "confidence": 0.7,
                "permutation": [1, 0, 2],
            },
        ]
        dspy.configure(lm=dspy.utils.dummies.DummyLM(canned))
        return

    model = os.environ.get("HIVEMIND_DSPY_LM")
    if not model:
        raise RuntimeError(
            "Set HIVEMIND_DSPY_LM=<litellm model id> or HIVEMIND_DSPY_DRY_RUN=1."
        )
    dspy.configure(lm=dspy.LM(model))
