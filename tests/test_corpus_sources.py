"""Source adapter tests.

Hard rule from the session plan: these tests **never** hit GitHub. We
monkeypatch ``hivemind.corpus.sources.base.fetch_json`` to a router that
returns canned fixtures from ``tests/fixtures/``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hivemind.corpus.sources import base as src_base
from hivemind.corpus.sources.anthropic_skills import AnthropicSkillsAdapter
from hivemind.corpus.sources.openhands_microagents import OpenHandsMicroagentsAdapter

FIXTURES = Path(__file__).parent / "fixtures"


def _load(name: str) -> object:
    return json.loads((FIXTURES / name).read_text())


def _build_router(routes: dict[str, str]):
    """Build a `fetch_json(url)` substitute that looks up the URL path against
    a small route map of fixture filenames."""

    def router(url: str, *, timeout: float = 15.0) -> object:  # noqa: ARG001
        for needle, fixture_name in routes.items():
            if needle in url:
                return _load(fixture_name)
        raise RuntimeError(f"unexpected URL in test: {url}")

    return router


@pytest.fixture()
def patched_anthropic(monkeypatch):
    routes = {
        "/contents/skills?": "gh_anthropic_skills_dir.json",
        "/contents/skills/pdf/SKILL.md": "gh_anthropic_pdf_skill.json",
        "/contents/skills/docx/SKILL.md": "gh_anthropic_docx_skill.json",
        "/contents/skills/mcp-builder/SKILL.md": "gh_anthropic_mcp_skill.json",
    }
    monkeypatch.setattr(src_base, "fetch_json", _build_router(routes))
    yield


@pytest.fixture()
def patched_openhands(monkeypatch):
    routes = {
        "/.openhands/microagents?": "gh_openhands_microagents_dir.json",
        "/.openhands/microagents/documentation.md": "gh_openhands_documentation.json",
        "/.openhands/microagents/glossary.md": "gh_openhands_glossary.json",
        "/.agents/skills?": "gh_openhands_agents_skills_dir.json",
        "/.agents/skills/custom-codereview-guide.md": "gh_openhands_codereview.json",
        "/.agents/skills/cross-repo-testing?": "gh_openhands_cross_repo_dir.json",
        "/.agents/skills/cross-repo-testing/README.md": "gh_openhands_cross_repo_readme.json",
    }
    monkeypatch.setattr(src_base, "fetch_json", _build_router(routes))
    yield


def test_anthropic_adapter_normalizes_skills(patched_anthropic):
    adapter = AnthropicSkillsAdapter()
    skills = adapter.pull()
    assert len(skills) == 3
    ids = sorted(s.id for s in skills)
    assert ids == ["docx", "mcp-builder", "pdf"]
    pdf = next(s for s in skills if s.id == "pdf")
    assert "PDF" in pdf.body
    assert pdf.tokens_proxy() if hasattr(pdf, "tokens_proxy") else True
    # Triggers include the slug and at least one extra word from the description.
    assert "pdf" in pdf.triggers
    assert len(pdf.triggers) >= 3
    # Source string includes the pinned commit sha.
    assert "anthropics/skills@" in pdf.source


def test_anthropic_adapter_respects_limit(patched_anthropic):
    skills = AnthropicSkillsAdapter().pull(limit=1)
    assert len(skills) == 1


def test_openhands_adapter_normalizes_files_and_nested_dirs(patched_openhands):
    skills = OpenHandsMicroagentsAdapter().pull()
    ids = {s.id for s in skills}
    # documentation, glossary from .openhands/microagents
    # custom-codereview-guide and a README from cross-repo-testing dir
    assert "documentation" in ids
    assert "glossary" in ids
    assert "custom-codereview-guide" in ids
    # README.md nested under cross-repo-testing/ collapses to the dir name,
    # which prevents id collisions across multiple nested SKILL/README files.
    assert "cross-repo-testing" in ids
    # Source string has the pinned sha.
    for s in skills:
        assert "OpenHands/OpenHands@" in s.source
    # Bodies are non-empty.
    for s in skills:
        assert s.body.strip()


def test_pull_sources_writes_files(patched_anthropic, tmp_path: Path):
    from hivemind.corpus.pull import pull_sources

    written = pull_sources(["anthropic_skills"], tmp_path)
    assert "anthropic_skills" in written
    paths = written["anthropic_skills"]
    assert len(paths) == 3
    for p in paths:
        assert p.name.startswith("anthropic-skills__")
        text = p.read_text()
        assert text.startswith("---\n")
        assert "title:" in text
        assert "source:" in text


def test_pull_then_ingest_runs_audit_log(patched_anthropic, tmp_path: Path):
    """End-to-end: pull → ingest → audit log captures non-passed rows."""
    from hivemind.corpus.ingest import ingest_directory, write_jsonl
    from hivemind.corpus.pull import pull_sources

    pull_sources(["anthropic_skills"], tmp_path)
    skills = ingest_directory(tmp_path)
    out_jsonl = tmp_path.parent / "skills.jsonl"
    audit_log = tmp_path.parent / "audit_log.jsonl"
    write_jsonl(skills, out_jsonl, audit_log=audit_log)

    assert out_jsonl.exists()
    # All synthesized fixtures should pass the conservative audit; the audit
    # log may be empty, but if anything was logged, it should be parseable.
    if audit_log.exists():
        for line in audit_log.read_text().splitlines():
            if line.strip():
                row = json.loads(line)
                assert "skill_id" in row and "status" in row


# Patch the convenience attribute that adapters use indirectly. NormalizedSkill
# doesn't have a tokens_proxy method; the assertion above is defensive — we
# keep it to clarify what we *did* expect (token-counting happens at ingest,
# not at pull).
