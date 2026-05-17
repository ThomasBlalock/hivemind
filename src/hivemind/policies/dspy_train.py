"""Offline trainer for System 2.

Produces three artifact files under ``models/dspy/<version>/`` that
``DSPyCompiledPolicy`` loads at serve time:

- ``distillations.jsonl`` — one row per ``{skill_id, model, body}``.
- ``selector.json``       — ``{skill_id: {model: {logit: float}}}``.
- ``order_prior.json``    — ``{skill_id: {model: float}}`` position prior.

The training reward stand-in is intentionally cheap and synthetic so the
trainer runs without an external evaluator. The plan is to swap in the eval
harness's success rate as the real reward once Phase 1 measurements stabilize —
see docs/context_injection/02_dspy_compiled_skills.md.

CLI:
    hivemind dspy train --out-version v1 --max-lm-calls 100
    hivemind dspy train --dry-run        # no network, uses DummyLM

Direct invocation:
    HIVEMIND_DSPY_DRY_RUN=1 python -m hivemind.policies.dspy_train
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Pull OPENROUTER_API_KEY (or whichever provider HIVEMIND_DSPY_LM routes to)
# out of repo-root .env before configure_lm() reads the environment.
load_dotenv()

from hivemind.config import default_corpus_path, models_dir  # noqa: E402
from hivemind.corpus.ingest import load_jsonl  # noqa: E402
from hivemind.corpus.schema import Skill  # noqa: E402
from hivemind.tokenize import count_tokens  # noqa: E402

# Target models we distill for. Keep this small until per-model lift is proven.
DEFAULT_TARGET_MODELS = (
    "claude-haiku-4-5",
    "claude-sonnet-4-6",
    "claude-opus-4-7",
)


def _require_dspy():
    try:
        import dspy  # noqa: F401
    except ImportError as e:
        raise RuntimeError(
            "dspy-ai not installed. Install with: pip install -e '.[dspy]'"
        ) from e


# --- LM call counter (hard budget cap) ------------------------------------


class _CallCounter:
    """Tally LM calls so the trainer can abort before blowing the budget."""

    def __init__(self, cap: int):
        self.cap = cap
        self.count = 0

    def hit(self) -> None:
        self.count += 1
        if self.cap and self.count > self.cap:
            raise RuntimeError(
                f"LM call budget exceeded: {self.count} > {self.cap}. Aborting."
            )


# --- synthetic reward signal ----------------------------------------------


def _distill_reward(raw_body: str, distilled: str) -> float:
    """Tiny synthetic reward for distillation.

    Reward = 1 if the distilled body is shorter AND contains at least one
    'actionable' keyword. Stand-in until the eval harness can supply the real
    success-rate-delta signal.
    """
    if not distilled or distilled.strip() == raw_body.strip():
        return 0.0
    if count_tokens(distilled) >= count_tokens(raw_body):
        return 0.0
    keywords = ("command", "step", "run", "use", "call", "$", "```")
    if not any(k in distilled.lower() for k in keywords):
        return 0.0
    return 1.0


def _select_reward(prediction, expected_include: bool) -> float:
    """Reward 1 if the selector's ``include`` matches the small hand-labeled
    set we synthesize in ``_select_examples``."""
    return 1.0 if bool(getattr(prediction, "include", False)) == expected_include else 0.0


# --- training data --------------------------------------------------------


def _select_examples(skills: list[Skill]):
    """Hand-labeled tiny set: for each skill, a query that should hit and a
    decoy query that should miss. Generated deterministically from triggers."""
    import dspy

    examples = []
    for s in skills:
        trig = s.triggers[0] if s.triggers else s.title
        # Positive: query mentions the trigger; expected include=True.
        examples.append(
            dspy.Example(
                query=f"how do I {trig}?",
                skill_candidate=f"{s.title}\n\n{s.body[:400]}",
                target_model=DEFAULT_TARGET_MODELS[0],
                include=True,
                confidence=0.9,
            ).with_inputs("query", "skill_candidate", "target_model")
        )
        # Negative: unrelated query; expected include=False.
        examples.append(
            dspy.Example(
                query="what is the weather today",
                skill_candidate=f"{s.title}\n\n{s.body[:400]}",
                target_model=DEFAULT_TARGET_MODELS[0],
                include=False,
                confidence=0.9,
            ).with_inputs("query", "skill_candidate", "target_model")
        )
    return examples


# --- artifact writers ------------------------------------------------------


def _write_distillations(path: Path, rows: list[dict]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    return len(rows)


def _write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True))


# --- main loops -----------------------------------------------------------


def _train_distillations(skills: list[Skill], counter: _CallCounter) -> list[dict]:
    """Run the distiller over each (skill × target_model). One LM call each.

    Records only those distillations whose synthetic reward > 0, so the
    artifact reflects the optimizer's keep-set rather than every call.
    """
    from hivemind.policies.dspy_programs import SkillDistiller

    distiller = SkillDistiller()
    rows: list[dict] = []
    for skill in skills:
        for model in DEFAULT_TARGET_MODELS:
            counter.hit()
            try:
                distilled = distiller(skill.body, model)
            except RuntimeError as e:
                if "LM call budget exceeded" in str(e):
                    raise
                continue
            except Exception:  # noqa: BLE001 — single-call failures shouldn't kill the run
                continue
            if _distill_reward(skill.body, distilled) > 0:
                rows.append({"skill_id": skill.id, "model": model, "body": distilled})
    return rows


def _train_selector(skills: list[Skill], counter: _CallCounter) -> dict:
    """Per-skill, per-model inclusion logit derived from selector behavior on
    a tiny synthetic positive/negative pair. logit ≈ P(include | pos) - P(include | neg).
    """
    from hivemind.policies.dspy_programs import SkillSelector

    selector = SkillSelector()
    examples = _select_examples(skills)

    # Index examples by (skill_id, label) for paired computation.
    by_skill: dict[str, dict[bool, list]] = {}
    for skill in skills:
        by_skill[skill.id] = {True: [], False: []}

    # Map examples back to skills by matching the title prefix (deterministic).
    skill_by_title = {s.title: s for s in skills}
    out: dict[str, dict[str, dict[str, float]]] = {}

    for ex in examples:
        title_prefix = ex.skill_candidate.split("\n", 1)[0]
        skill = skill_by_title.get(title_prefix)
        if skill is None:
            continue
        counter.hit()
        try:
            pred = selector(
                query=ex.query,
                skill_candidate=ex.skill_candidate,
                target_model=ex.target_model,
            )
        except RuntimeError as e:
            if "LM call budget exceeded" in str(e):
                raise
            continue
        except Exception:  # noqa: BLE001
            continue
        # Synthetic reward dictates "good" decisions; logit accumulates them.
        reward = _select_reward(pred, ex.include)
        out.setdefault(skill.id, {}).setdefault(ex.target_model, {"logit": 0.0})
        out[skill.id][ex.target_model]["logit"] += (1.0 if ex.include else -1.0) * reward

    return out


def _train_orderer(skills: list[Skill], counter: _CallCounter) -> dict:
    """Position prior: small positive bias for skills the orderer placed
    early on a synthetic multi-skill prompt.
    """
    from hivemind.policies.dspy_programs import SkillOrderer

    if not skills:
        return {}
    orderer = SkillOrderer()
    ids = [s.id for s in skills]
    out: dict[str, dict[str, float]] = {s.id: {} for s in skills}

    for model in DEFAULT_TARGET_MODELS:
        counter.hit()
        try:
            perm = orderer(
                selected_skill_ids=ids,
                query="debug a regression in a python script",
                target_model=model,
            )
        except RuntimeError as e:
            if "LM call budget exceeded" in str(e):
                raise
            continue
        except Exception:  # noqa: BLE001
            continue
        n = len(perm) or 1
        for new_pos, orig_idx in enumerate(perm):
            sid = ids[orig_idx]
            # Skills earlier in the permutation get a higher prior.
            out[sid][model] = round(1.0 - new_pos / n, 4)
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="hivemind-dspy-train")
    p.add_argument("--out-version", default="v1")
    p.add_argument(
        "--max-lm-calls", type=int, default=200,
        help="Hard cap on LM calls (across all programs). Defaults to 200."
    )
    p.add_argument(
        "--dry-run", action="store_true",
        help="Use dspy.DummyLM; no network calls.",
    )
    args = p.parse_args(argv)

    _require_dspy()

    if args.dry_run:
        os.environ["HIVEMIND_DSPY_DRY_RUN"] = "1"

    # Import lazily so configure_lm picks up the dry-run flag we just set.
    from hivemind.policies.dspy_programs import configure_lm
    configure_lm()

    corpus_path = default_corpus_path()
    if not corpus_path.exists():
        print(f"ERROR: corpus not found at {corpus_path}. Run `hivemind corpus build` first.", file=sys.stderr)
        return 2
    skills = [s for s in load_jsonl(corpus_path) if s.audit_status == "passed"]
    if not skills:
        print("ERROR: corpus has no audit-passed skills.", file=sys.stderr)
        return 2

    out_dir = models_dir() / "dspy" / args.out_version
    out_dir.mkdir(parents=True, exist_ok=True)
    counter = _CallCounter(args.max_lm_calls)

    print(f"Training on {len(skills)} skills, target models = {DEFAULT_TARGET_MODELS}")
    distillations = _train_distillations(skills, counter)
    selector = _train_selector(skills, counter)
    order_prior = _train_orderer(skills, counter)

    n_dist = _write_distillations(out_dir / "distillations.jsonl", distillations)
    _write_json(out_dir / "selector.json", selector)
    _write_json(out_dir / "order_prior.json", order_prior)

    print(
        f"LM calls used: {counter.count}/{counter.cap}\n"
        f"Distillations kept: {n_dist}\n"
        f"Selector entries: {sum(len(v) for v in selector.values())}\n"
        f"Order prior skills: {len(order_prior)}\n"
        f"Wrote artifacts to {out_dir}"
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
