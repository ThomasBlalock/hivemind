"""Source adapters: fetch + normalize external skill repos into our schema.

Each adapter exposes ``pull() -> list[NormalizedSkill]``. ``NormalizedSkill``
is the pre-Pydantic record that the corpus writer turns into our markdown
frontmatter files. Adapters pin a specific commit sha so the corpus is
reproducible.

To add a new source: subclass :class:`SourceAdapter`, implement ``pull``, and
register it in :data:`ADAPTERS`.
"""

from __future__ import annotations

from hivemind.corpus.sources.anthropic_skills import AnthropicSkillsAdapter
from hivemind.corpus.sources.base import NormalizedSkill, SourceAdapter
from hivemind.corpus.sources.openhands_microagents import OpenHandsMicroagentsAdapter

ADAPTERS: dict[str, type[SourceAdapter]] = {
    "anthropic_skills": AnthropicSkillsAdapter,
    "openhands_microagents": OpenHandsMicroagentsAdapter,
}

__all__ = [
    "ADAPTERS",
    "AnthropicSkillsAdapter",
    "NormalizedSkill",
    "OpenHandsMicroagentsAdapter",
    "SourceAdapter",
]
