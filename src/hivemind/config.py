"""Filesystem layout + defaults.

Override via env:
- HIVEMIND_CORPUS_DIR  (default: <repo>/corpus)
- HIVEMIND_RUNS_DIR    (default: <repo>/runs)
- HIVEMIND_MODELS_DIR  (default: <repo>/models)
"""

from __future__ import annotations

import os
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def corpus_dir() -> Path:
    return Path(os.environ.get("HIVEMIND_CORPUS_DIR") or _repo_root() / "corpus")


def runs_dir() -> Path:
    return Path(os.environ.get("HIVEMIND_RUNS_DIR") or _repo_root() / "runs")


def models_dir() -> Path:
    return Path(os.environ.get("HIVEMIND_MODELS_DIR") or _repo_root() / "models")


def default_corpus_path() -> Path:
    return corpus_dir() / "skills.jsonl"


def default_skills_src() -> Path:
    return corpus_dir() / "skills"
