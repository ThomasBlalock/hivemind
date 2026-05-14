# System 2 — DSPy-Compiled, Per-Model Skill Distillations

**Status:** designed. Implementation depends on Phase 1 measurements being stable. Tracked in [../../todo/plan.md](../../todo/plan.md) Phase 5.

Builds on [System 1](01_hybrid_retrieval.md) by replacing hand-tuned thresholds and human-written skill bodies with components optimized offline against eval-suite reward.

## Core idea

Skills as written are for humans. For a given (skill, target_model), we can usually express the same instruction in fewer tokens or in a phrasing that suits the model's prior. We use DSPy to optimize three pieces against eval success:

1. **Per-model distillation** of each skill body.
2. **A selection program** that replaces System 1's `τ` threshold.
3. **An ordering program** that picks the in-context order of selected skills.

DSPy's MIPROv2 / GEPA optimizers do the heavy lifting. We don't fine-tune any models.

## Components

### Distillation
- DSPy `SkillDistiller(raw_body, target_model) -> distilled_body`.
- Optimizer searches over phrasing/length/example-count.
- Reward: improvement in eval success rate when the distilled body is injected on tasks where System 1 chose this skill.
- Output stored as additional field per skill: `body_distilled_<model_id>`.

### Selection
- DSPy `SkillSelector(query, skill_candidate, model) -> include: bool, confidence: float`.
- Compiled against held-out tasks; learns per-model whether the skill helps.
- Replaces System 1's flat threshold with a learned predicate.

### Ordering
- DSPy `SkillOrderer(selected, query, model) -> permutation`.
- LLM attention is order-sensitive; small wins available here.

## Training

- **Train:** 80% of SWE-bench-Lite + 80% of Aider-polyglot, split at task-family level (e.g. by source repo). Random splits underestimate generalization gap for code tasks.
- **Held-out:** 20% of each, never touched during optimization.
- **Budget cap:** 10× the cost of one full baseline eval run, configurable in `src/policies/dspy_compiled/config.yaml`.
- **Warm start:** initialize selection from System 1's rerank-score threshold; initialize distillations as identity (raw body).

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| Overfits to eval distribution | Family-level split; ship only if held-out gain ≈ train gain |
| Distillation drops critical instructions | Every distilled skill spot-checked by a human before production; diff against raw saved in `models/dspy/v<n>/distillations.jsonl` |
| Optimization cost balloons | Hard budget cap; parallelize across 16 workers; cache LLM calls aggressively |
| Per-model proliferation | Initially compile for ≤3 models (Haiku, Sonnet, Opus); skip distillation for low-traffic models |

## What this still can't do

| Limitation | Fixed by |
|---|---|
| One synthesis call per trajectory; no mid-trajectory adaptation | [System 3](03_online_bandit.md) |
| Frozen at compile-time — production outcomes don't update it | [System 3](03_online_bandit.md) |
| Can't react to "the agent is stuck" signal | [System 3](03_online_bandit.md) |

## Implementation

- File: `src/policies/dspy_compiled.py` (policy) + `src/policies/dspy_compiled/train.py` (optimizer)
- Compiled artifacts under `models/dspy/v<n>/` (versioned with the corpus sha)
- Same [API](../agent_harness/integration.md) as System 1; clients see only `policy: "dspy_compiled@v1"` in the response

## Dependencies

- `dspy-ai`
- All of System 1's dependencies (this policy inherits its retrieval frontend; only the selection/ordering tail changes)
