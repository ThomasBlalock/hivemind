"""Tests for the eval_tasks/ directory.

For every task directory:
- ``task.yaml`` parses to the expected shape.
- ``repo/`` contains at least one pytest test.
- Running the task's own ``test_cmd`` against the unmodified repo **fails**
  — that's the agent's job to fix. We assert it fails to catch the
  "I forgot to introduce the bug" mistake.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
import yaml

EVAL_DIR = Path(__file__).resolve().parents[1] / "eval_tasks"


def _task_dirs() -> list[Path]:
    return sorted(p for p in EVAL_DIR.iterdir() if p.is_dir())


@pytest.mark.parametrize("task_dir", _task_dirs(), ids=lambda p: p.name)
def test_task_yaml_shape(task_dir: Path):
    spec_path = task_dir / "task.yaml"
    assert spec_path.exists(), f"missing {spec_path}"
    spec = yaml.safe_load(spec_path.read_text())
    assert isinstance(spec, dict)
    assert spec.get("id") == task_dir.name
    assert isinstance(spec.get("prompt"), str) and spec["prompt"].strip()
    assert isinstance(spec.get("test_cmd"), str) and spec["test_cmd"].strip()
    # repo/ must exist with at least one .py file.
    repo = task_dir / "repo"
    assert repo.is_dir(), f"missing {repo}"
    pys = list(repo.glob("*.py"))
    assert any(p.name.startswith("test_") for p in pys), (
        f"{task_dir.name} has no test_*.py under repo/"
    )


@pytest.mark.parametrize("task_dir", _task_dirs(), ids=lambda p: p.name)
def test_task_test_fails_on_unmodified_repo(task_dir: Path):
    """The bug must actually be present — running the test command on the
    untouched repo should fail."""
    spec = yaml.safe_load((task_dir / "task.yaml").read_text())
    test_cmd = spec["test_cmd"]
    repo = task_dir / "repo"
    # Run with the venv's python and a clean PYTHONPATH so the tests resolve
    # the in-repo module instead of any installed package with the same name.
    env = {"PATH": f"{Path(sys.executable).parent}:/usr/bin:/bin"}
    result = subprocess.run(
        test_cmd, shell=True, cwd=repo, capture_output=True, timeout=60, env=env
    )
    assert result.returncode != 0, (
        f"{task_dir.name}: expected the bug to cause test failure, but tests "
        f"passed on the unmodified repo.\nstdout:\n{result.stdout.decode()}\n"
        f"stderr:\n{result.stderr.decode()}"
    )
