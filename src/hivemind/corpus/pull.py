"""Top-level entry point for ``hivemind corpus pull``.

Given a list of registered source names, fetch each, write one markdown file
per skill under ``corpus/skills/``, and emit a per-source summary so the user
can run ``hivemind corpus build`` next.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from pathlib import Path

from hivemind.corpus.sources import ADAPTERS
from hivemind.corpus.sources.base import NormalizedSkill, slugify

log = logging.getLogger(__name__)

# Files written by `corpus pull` go through ingest later; we keep them
# distinguished from hand-authored toy skills with a source-prefix in the
# filename: ``<source>__<id>.md``.


def write_skill_file(out_dir: Path, source_name: str, skill: NormalizedSkill) -> Path:
    """Write one normalized skill to disk in our frontmatter format.

    The source-name prefix in the filename prevents collisions across sources.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    fname = f"{slugify(source_name)}__{skill.id}.md"
    path = out_dir / fname
    import yaml

    frontmatter = {
        "id": f"{source_name}__{skill.id}",
        "title": skill.title,
        "description": skill.description,
        "triggers": skill.triggers,
        "source": skill.source,
    }
    meta_yaml = yaml.safe_dump(frontmatter, sort_keys=False, allow_unicode=True).strip()
    text = f"---\n{meta_yaml}\n---\n\n{skill.body.strip()}\n"
    path.write_text(text)
    return path


def pull_sources(
    sources: Iterable[str],
    out_dir: Path,
    *,
    limit_per_source: int | None = None,
) -> dict[str, list[Path]]:
    """Pull each named source and return per-source list of written paths."""
    written: dict[str, list[Path]] = {}
    for name in sources:
        adapter_cls = ADAPTERS.get(name)
        if adapter_cls is None:
            raise ValueError(f"unknown source: {name}. known: {sorted(ADAPTERS)}")
        adapter = adapter_cls()
        log.info("pulling %s …", name)
        skills = adapter.pull(limit=limit_per_source)
        paths: list[Path] = []
        for s in skills:
            paths.append(write_skill_file(out_dir, name, s))
        written[name] = paths
    return written
