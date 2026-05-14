"""Shared fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

from hivemind.corpus.ingest import ingest_directory, write_jsonl
from hivemind.corpus.schema import Skill


REPO = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def toy_corpus_dir() -> Path:
    return REPO / "corpus" / "skills"


@pytest.fixture(scope="session")
def toy_skills(toy_corpus_dir: Path) -> list[Skill]:
    return ingest_directory(toy_corpus_dir)


@pytest.fixture()
def built_corpus(tmp_path: Path, toy_corpus_dir: Path) -> Path:
    """Build a fresh jsonl in a temp dir so tests don't fight over corpus/skills.jsonl."""
    skills = ingest_directory(toy_corpus_dir)
    out = tmp_path / "skills.jsonl"
    write_jsonl(skills, out)
    return out


@pytest.fixture()
def isolated_corpus(monkeypatch, built_corpus: Path):
    """Point HIVEMIND_CORPUS_DIR at the temp corpus so default_corpus_path() returns it."""
    monkeypatch.setenv("HIVEMIND_CORPUS_DIR", str(built_corpus.parent))
    # Reset hub so policy singletons rebuild against the new corpus.
    from hivemind.api import hub
    hub.reset()
    yield built_corpus
    hub.reset()
