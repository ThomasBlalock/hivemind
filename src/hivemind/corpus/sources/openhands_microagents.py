"""Adapter for ``OpenHands/OpenHands`` microagents.

Pulls markdown files from ``.openhands/microagents/`` and ``.agents/skills/``
at a pinned commit. OpenHands microagents are plain markdown — no
frontmatter — so we synthesize triggers from the first heading and the
filename.
"""

from __future__ import annotations

import logging

from hivemind.corpus.sources.base import (
    NormalizedSkill,
    SourceAdapter,
    gh_contents,
    gh_file_text,
    slugify,
)

log = logging.getLogger(__name__)


OWNER = "OpenHands"
REPO = "OpenHands"
# Pinned commit. Bump intentionally when refreshing the corpus.
COMMIT_SHA = "e7b5e3079592a1cffb3fb64b8e0813b007ebbb2f"
# Pull from both locations.
SKILL_PATHS = (".openhands/microagents", ".agents/skills")


class OpenHandsMicroagentsAdapter(SourceAdapter):
    name = "openhands_microagents"

    def __init__(
        self,
        owner: str = OWNER,
        repo: str = REPO,
        ref: str = COMMIT_SHA,
        skill_paths: tuple[str, ...] = SKILL_PATHS,
    ):
        self._owner = owner
        self._repo = repo
        self._ref = ref
        self._skill_paths = skill_paths

    @property
    def source_string(self) -> str:
        return f"{self._owner}/{self._repo}@{self._ref}"

    def pull(self, limit: int | None = None) -> list[NormalizedSkill]:
        out: list[NormalizedSkill] = []
        for base_path in self._skill_paths:
            out.extend(self._pull_dir(base_path, limit=limit - len(out) if limit else None))
            if limit is not None and len(out) >= limit:
                break
        return out

    def _pull_dir(self, base_path: str, *, limit: int | None = None) -> list[NormalizedSkill]:
        try:
            index = gh_contents(self._owner, self._repo, base_path, ref=self._ref)
        except RuntimeError as e:
            log.warning("skip %s: %s", base_path, e)
            return []
        if not isinstance(index, list):
            return []

        out: list[NormalizedSkill] = []
        for entry in index:
            if limit is not None and len(out) >= limit:
                break
            etype = entry.get("type")
            name = entry["name"]
            if etype == "file" and name.endswith(".md"):
                text = self._fetch_file(entry["path"])
                if text:
                    out.append(self._normalize(name, entry["path"], text))
            elif etype == "dir":
                # Some skills are nested one level deep (.agents/skills/<name>/<file>.md).
                inner = gh_contents(self._owner, self._repo, entry["path"], ref=self._ref)
                if not isinstance(inner, list):
                    continue
                for child in inner:
                    if child.get("type") == "file" and child["name"].endswith(".md"):
                        text = self._fetch_file(child["path"])
                        if text:
                            out.append(self._normalize(child["name"], child["path"], text))
                            if limit is not None and len(out) >= limit:
                                break
        return out

    def _fetch_file(self, path: str) -> str | None:
        try:
            return gh_file_text(self._owner, self._repo, path, ref=self._ref)
        except RuntimeError as e:
            log.warning("skip file %s: %s", path, e)
            return None

    def _normalize(self, filename: str, path: str, text: str) -> NormalizedSkill:
        body = text.strip()
        # Title: first markdown heading, else filename without extension.
        title = filename.rsplit(".", 1)[0].replace("-", " ").replace("_", " ").title()
        for line in body.splitlines():
            if line.startswith("#"):
                title = line.lstrip("#").strip() or title
                break
        # Description: first paragraph after the heading.
        description = self._first_paragraph(body)
        triggers = self._derive_triggers(filename, description)
        # Id: filename stem, unless the file is a generic README / SKILL /
        # INDEX — in those cases use the parent directory name, since the
        # filename alone collides across nested skill folders.
        stem = filename.rsplit(".", 1)[0]
        if stem.lower() in {"skill", "readme", "index"}:
            parts = [p for p in path.split("/") if p]
            if len(parts) >= 2:
                stem = parts[-2]
        sid = slugify(stem)
        return NormalizedSkill(
            id=sid,
            title=title,
            description=description[:280],
            triggers=triggers,
            body=body,
            source=self.source_string,
            extra={"source_path": path},
        )

    @staticmethod
    def _first_paragraph(body: str) -> str:
        lines: list[str] = []
        for line in body.splitlines():
            line = line.rstrip()
            if line.startswith("#"):
                continue
            if not line:
                if lines:
                    break
                continue
            lines.append(line)
            if sum(len(line_) for line_ in lines) > 240:
                break
        return " ".join(lines).strip()

    @staticmethod
    def _derive_triggers(filename: str, description: str) -> list[str]:
        triggers: list[str] = [filename.rsplit(".", 1)[0].replace("-", " ").replace("_", " ")]
        if description:
            first = description.split(".")[0].lower()
            words = [w.strip(",.;:'\"`") for w in first.split() if len(w) > 3]
            triggers.extend(words[:6])
        seen: set[str] = set()
        unique: list[str] = []
        for t in triggers:
            tt = str(t).strip().lower()
            if tt and tt not in seen:
                seen.add(tt)
                unique.append(tt)
        return unique
