"""Offline trainer for System 2. Skeleton only.

To run real optimization you need:
- Eval harness installed and SWE-bench-Lite / Aider-polyglot runnable.
- `dspy-ai` installed (``pip install -e .[dspy]``).
- A funded LLM key for the optimizer's inner LLM calls.

This script defines the *shape* of the optimization. It is intentionally
not invoked from CI; calling ``main()`` without those preconditions raises.
See docs/context_injection/02_dspy_compiled_skills.md.
"""

from __future__ import annotations

import json
from pathlib import Path

from hivemind.config import default_corpus_path, models_dir
from hivemind.corpus.ingest import load_jsonl


def _require_dspy():
    try:
        import dspy  # noqa: F401
    except ImportError as e:
        raise RuntimeError(
            "dspy-ai not installed. Install with: pip install -e '.[dspy]'"
        ) from e


def main(out_version: str = "v1") -> Path:
    _require_dspy()
    skills = [s for s in load_jsonl(default_corpus_path()) if s.audit_status == "passed"]
    out_dir = models_dir() / "dspy" / out_version
    out_dir.mkdir(parents=True, exist_ok=True)

    # TODO(plan Phase 5 / System 2):
    # 1. Define DSPy programs: SkillDistiller, SkillSelector, SkillOrderer.
    # 2. Wire them to the eval harness as the reward signal (success per token).
    # 3. Run MIPROv2 / GEPA with the configured budget cap.
    # 4. Persist results to distillations.jsonl, selector.json, order_prior.json.

    # Emit empty artifacts so the serve-time policy has well-formed files to load.
    (out_dir / "distillations.jsonl").write_text("")
    (out_dir / "selector.json").write_text(json.dumps({}))
    (out_dir / "order_prior.json").write_text(json.dumps({}))
    return out_dir


if __name__ == "__main__":  # pragma: no cover
    print(main())
