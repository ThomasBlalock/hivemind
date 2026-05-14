"""Normalize source skill files into the canonical schema.

Walks `corpus/skills/*.md`, parses frontmatter, runs the security audit, and
emits `corpus/skills.jsonl`. See docs/skills_corpus/ingestion.md.

Side effect: when ingestion sees a skill that isn't ``passed``, it appends a
row to ``corpus/audit_log.jsonl`` so the user can see exactly which skill /
source / pattern tripped the audit without rerunning the pipeline.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from datetime import UTC, datetime
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


def append_audit_log(audit_log: Path, skill: Skill) -> None:
    """Append one row to the audit log. Caller is expected to have decided
    that this skill warrants logging (not 'passed')."""
    audit_log.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "timestamp": datetime.now(UTC).isoformat(),
        "skill_id": skill.id,
        "source": skill.source,
        "status": skill.audit_status,
        "notes": list(skill.audit_notes),
    }
    with audit_log.open("a") as f:
        f.write(json.dumps(row) + "\n")


def write_jsonl(
    skills: Iterable[Skill],
    out_path: Path,
    *,
    audit_log: Path | None = None,
) -> int:
    """Write all non-failed skills as jsonl; append failed / manual_review rows
    to the optional ``audit_log``.

    The audit log defaults to ``<corpus_dir>/audit_log.jsonl`` if not provided.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if audit_log is None:
        audit_log = out_path.parent / "audit_log.jsonl"
    n = 0
    with out_path.open("w") as f:
        for s in skills:
            if s.audit_status != "passed":
                append_audit_log(audit_log, s)
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
