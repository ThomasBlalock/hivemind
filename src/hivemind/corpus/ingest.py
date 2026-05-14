"""Normalize source skill files into the canonical schema.

Walks `corpus/skills/*.md`, parses frontmatter, runs the security audit, and
emits `corpus/skills.jsonl`. See docs/skills_corpus/ingestion.md.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path

import frontmatter

from hivemind.corpus.schema import Skill
from hivemind.corpus.security_audit import audit_body
from hivemind.tokenize import count_tokens


def parse_skill_file(path: Path) -> Skill:
    post = frontmatter.load(path)
    meta = post.metadata
    body = post.content.strip()
    skill_id = meta.get("id") or path.stem

    audit = audit_body(body)

    return Skill(
        id=skill_id,
        title=meta.get("title", skill_id),
        description=meta.get("description", ""),
        triggers=list(meta.get("triggers", [])),
        body=body,
        source=meta.get("source", f"local:{path.name}"),
        tokens=count_tokens(body),
        audit_status=audit.status,  # type: ignore[arg-type]
        audit_notes=audit.notes,
    )


def ingest_directory(src_dir: Path) -> list[Skill]:
    skills = []
    for p in sorted(src_dir.glob("*.md")):
        skills.append(parse_skill_file(p))
    return skills


def write_jsonl(skills: Iterable[Skill], out_path: Path) -> int:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with out_path.open("w") as f:
        for s in skills:
            # Drop skills that hard-failed audit. manual_review_required ones
            # are kept but marked so a human can decide.
            if s.audit_status == "failed":
                continue
            f.write(s.model_dump_json() + "\n")
            n += 1
    return n


def load_jsonl(path: Path) -> list[Skill]:
    skills = []
    with path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            skills.append(Skill(**json.loads(line)))
    return skills
