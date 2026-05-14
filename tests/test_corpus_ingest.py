from __future__ import annotations

from pathlib import Path

from hivemind.corpus.ingest import ingest_directory, load_jsonl, write_jsonl


def test_ingest_toy_corpus_yields_three_skills(toy_corpus_dir: Path):
    skills = ingest_directory(toy_corpus_dir)
    ids = {s.id for s in skills}
    assert ids == {"git-bisect", "python-debugging", "regex-construction"}


def test_all_toy_skills_pass_audit(toy_skills):
    for s in toy_skills:
        assert s.audit_status == "passed", (s.id, s.audit_notes)


def test_token_count_nonzero(toy_skills):
    for s in toy_skills:
        assert s.tokens > 0


def test_write_and_load_roundtrip(tmp_path: Path, toy_skills):
    out = tmp_path / "skills.jsonl"
    n = write_jsonl(toy_skills, out)
    assert n == len(toy_skills)
    reloaded = load_jsonl(out)
    assert [s.id for s in reloaded] == [s.id for s in toy_skills]
