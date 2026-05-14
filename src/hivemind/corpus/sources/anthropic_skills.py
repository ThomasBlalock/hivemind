"""Adapter for the ``anthropics/skills`` GitHub repo.

Pins a specific commit so corpus rebuilds are reproducible. Update the
``COMMIT_SHA`` constant when intentionally refreshing the corpus.

Each skill is a directory under ``skills/<name>/`` containing a ``SKILL.md``
with YAML frontmatter (``name``, ``description``). We pull SKILL.md only —
auxiliary files (``forms.md``, ``reference.md``, ``scripts/``) are skipped
because they're not the trigger-shaped instruction the policy looks up.
"""

from __future__ import annotations

import logging

from hivemind.corpus.sources.base import (
    NormalizedSkill,
    SourceAdapter,
    gh_contents,
    gh_file_text,
    parse_frontmatter,
    slugify,
)

log = logging.getLogger(__name__)


OWNER = "anthropics"
REPO = "skills"
# Pinned commit. Bump intentionally when refreshing the corpus.
COMMIT_SHA = "f458cee31a7577a47ba0c9a101976fa599385174"
SKILLS_PATH = "skills"


class AnthropicSkillsAdapter(SourceAdapter):
    name = "anthropic_skills"

    def __init__(
        self,
        owner: str = OWNER,
        repo: str = REPO,
        ref: str = COMMIT_SHA,
        skills_path: str = SKILLS_PATH,
    ):
        self._owner = owner
        self._repo = repo
        self._ref = ref
        self._skills_path = skills_path

    @property
    def source_string(self) -> str:
        return f"{self._owner}/{self._repo}@{self._ref}"

    def pull(self, limit: int | None = None) -> list[NormalizedSkill]:
        index = gh_contents(self._owner, self._repo, self._skills_path, ref=self._ref)
        if not isinstance(index, list):
            raise RuntimeError(
                f"expected a directory listing at {self._skills_path}, got: {type(index).__name__}"
            )
        skill_dirs = [e for e in index if e.get("type") == "dir"]
        out: list[NormalizedSkill] = []
        for entry in skill_dirs:
            if limit is not None and len(out) >= limit:
                break
            name = entry["name"]
            md_path = f"{self._skills_path}/{name}/SKILL.md"
            try:
                text = gh_file_text(self._owner, self._repo, md_path, ref=self._ref)
            except RuntimeError as e:
                log.warning("skipping %s: %s", name, e)
                continue
            meta, body = parse_frontmatter(text)
            if not body:
                log.warning("skipping %s: empty body", name)
                continue
            description = (meta.get("description") or "").strip()
            triggers = self._derive_triggers(name, description, meta)
            out.append(
                NormalizedSkill(
                    id=slugify(name),
                    title=meta.get("name", name),
                    description=description,
                    triggers=triggers,
                    body=body,
                    source=self.source_string,
                    extra={"source_path": md_path},
                )
            )
        return out

    @staticmethod
    def _derive_triggers(name: str, description: str, meta: dict) -> list[str]:
        """Synthesize triggers from the directory name + the first noun-phrasey
        words in description. The upstream frontmatter doesn't carry triggers,
        so we cobble together a reasonable starter set."""
        triggers: list[str] = [name.replace("-", " "), name]
        if description:
            # Take the first sentence; chop to 6 short words; lowercase + dedupe.
            first = description.split(".")[0].lower()
            words = [w.strip(",.;:'\"") for w in first.split() if len(w) > 3]
            triggers.extend(words[:6])
        # Configured triggers in frontmatter would win — keep this hook in.
        configured = meta.get("triggers")
        if isinstance(configured, list):
            triggers = [*[str(t) for t in configured], *triggers]
        # Dedupe preserving order.
        seen: set[str] = set()
        unique: list[str] = []
        for t in triggers:
            tt = str(t).strip().lower()
            if tt and tt not in seen:
                seen.add(tt)
                unique.append(tt)
        return unique
