# Harness Integration Plan

Aim: integrate HiveMind into a real, existing agent harness end-to-end, validate the idea on at least one coding task with multiple models via OpenRouter, then escalate to a marquee target (Hermes, OpenHands) if results look good.

Status: **research complete. Implementation in progress.**

---

## Candidate harnesses

| Harness | Language | OpenRouter | Injection point | Setup cost | Verdict |
|---|---|---|---|---|---|
| **mini-swe-agent** | Python | yes (via LiteLLM) | configurable `system_template`, linear message history | very low | **chosen** |
| Aider | Python | yes (native) | `--read <file>` (just adds files to context) | low | strong plan-B |
| SWE-agent | Python | yes (LiteLLM) | yaml config + demonstrations | medium | superseded by mini-swe-agent per upstream |
| OpenHands | Python | yes (LiteLLM) | microagents | high (Docker) | phase 2 / marquee target |
| goose | Rust + Python | provider plugin | "hints" md | medium | docs migrating; revisit later |
| Continue.dev | TS (VS Code) | yes | `.continue/prompts/` | high (extension automation) | skip |

## Why mini-swe-agent

The 100-line agent from the SWE-agent team. Confirmed during research:

- `pip install mini-swe-agent` exists.
- Python API: `DefaultAgent(LitellmModel(model_name=...), LocalEnvironment()).run(task)`.
- LiteLLM under the hood → OpenRouter works via `model_name="openrouter/anthropic/claude-sonnet-4"` (and similar).
- Cost is tracked automatically via `litellm.cost_calculator.completion_cost()` and reported in the message stream — we get cost for free without bolting on LiteLLM proxy.
- The `AgentConfig` Pydantic model exposes `system_template` and the runtime exposes `extra_template_vars` — both clean injection points for skill chunks.
- Linear message history is exactly what System 3's mid-trajectory design assumes.

Why not Aider (kept as plan-B):
- Aider's `--read` is essentially baseline B with a different file path — it dumps a file into context. Doesn't exercise turn-by-turn injection.
- Python API explicitly unsupported per their docs.
- Token-cost reporting unclear; mini-swe-agent gives it to us via LiteLLM.
- Shell-out costs us programmatic control over which turn the injection fires on.

Sources:
- [mini-swe-agent GitHub](https://github.com/SWE-agent/mini-swe-agent)
- [mini-swe-agent DefaultAgent source](https://github.com/SWE-agent/mini-swe-agent/blob/main/src/minisweagent/agents/default.py)
- [LitellmModel source](https://github.com/SWE-agent/mini-swe-agent/blob/main/src/minisweagent/models/litellm_model.py)
- [aider OpenRouter docs](https://aider.chat/docs/llms/openrouter.html)
- [aider scripting](https://aider.chat/docs/scripting.html) (note: unsupported)
- [aider options reference](https://aider.chat/docs/config/options.html)

## Why OpenRouter

- One API key → 100+ models (Anthropic, OpenAI, Meta, Mistral, Google, Qwen, DeepSeek, etc.).
- LiteLLM has a built-in OpenRouter provider — model name `openrouter/<provider>/<model>` routes automatically.
- Cost accounting consolidated per API key, no per-provider sign-ups.
- Sufficient for our "mid-tier model + HiveMind ≈ top-tier model" claim because we can sweep across tiers trivially.

## Integration design

```
┌────────────────────────────────────┐
│  hivemind.harness.mini_swe_runner  │
│                                    │
│  for each turn:                    │
│    1. ask /synthesize for skills   │
│    2. splice into system prompt    │
│       via extra_template_vars      │
│    3. let DefaultAgent step()      │
│  on completion:                    │
│    POST /feedback (for System 3)   │
└────────────────────────────────────┘
                  │
                  ▼
            mini-swe-agent
                  │
                  ▼
            LiteLLM ──► openrouter/<model>
```

Two integration depths, both built:
- **Static injection**: call `/synthesize` once with the task prompt, splice chunks into `system_template`. Validates Systems 1 & 2.
- **Dynamic injection**: call `/synthesize` on every turn with the conversation so far, append new chunks as system messages. Validates System 3's mid-trajectory design.

## Test tasks

Small Python bug-fix tasks, each in `eval_tasks/<task_id>/`:
- `task.yaml` — name, prompt, target file, test command
- `repo/` — the buggy code + a failing pytest

Each task is self-contained: copy the dir to a tmpdir, let the agent edit it, run pytest, score 1 if green.

Initial set (3 tasks):
1. `fizzbuzz_off_by_one` — classic off-by-one in a fizzbuzz function. Easy. Any model should solve.
2. `regex_backref` — broken regex that should match repeated words. Medium. Tests the regex-construction skill specifically.
3. `git_history_bug` — script that walks git log incorrectly. Harder. Tests the python-debugging + tool-use combo.

If HiveMind helps, we should see the gap between baseline and HiveMind-injected widen on tasks 2 and 3 (where the relevant skill exists in the corpus) and stay flat on task 1 (no relevant skill).

## Evaluation protocol

- For each cell of `(policy ∈ {baseline_a, baseline_b, hybrid_retrieval}) × (model ∈ chosen list) × (task)`:
  - 3 runs (variance)
  - Record: success (test green/red), cost USD, tokens, turns, runtime
- Output CSV + a short markdown report.
- Initial model list (cheap → expensive): `qwen-2.5-coder-7b`, `claude-haiku`, `claude-sonnet`. Cap total cost via OpenRouter per-key spend limit before running.

## Implementation phases

1. [x] Research → finalize this plan.
2. [x] Wrapper: [`src/hivemind/harness/mini_swe_runner.py`](../src/hivemind/harness/mini_swe_runner.py) with `run_task(task_spec, *, model, policy_name, ..., dynamic=False)`. Both static and dynamic mid-trajectory injection implemented.
3. [x] Tasks: 2 fixtures under [`eval_tasks/`](../eval_tasks/) — `fizzbuzz_off_by_one` (easy) and `regex_backref` (medium). Each carries `task.yaml` + a `repo/` with the buggy code and a pytest test_cmd.
4. [x] Sweep script: [`scripts/run_harness_sweep.py`](../scripts/run_harness_sweep.py). Each (run × task × model × policy) cell runs in an isolated tmp-copy of the repo; writes a CSV.
5. [x] Mocked verification — `--dry-run` mode swaps in mini-swe-agent's `DeterministicModel`; the full sweep runs end-to-end (corpus build → policy registry → adapter → agent loop → grading) with zero network calls. Test in `tests/test_mini_swe_runner.py` ensures this never regresses.
6. [x] **One-command real run** documented at the top of the sweep script.
7. [ ] **Deferred:** mirror the wrapper to Aider (kept as plan-B; mini-swe-agent integration is sufficient for the first claim).

## Risks / mitigations

| Risk | Mitigation |
|---|---|
| `mini-swe-agent` shell tool can be slow or error-prone in WSL | Time-cap per task; isolate each run in `tmpdir` |
| LiteLLM cost calculation fails for some OpenRouter routes | Treat missing cost as `None`, still record success |
| HiveMind's `/synthesize` adds 100–200 ms per turn | Pre-warm policy at sweep start; report HiveMind latency separately |
| Toy corpus (3 skills) won't move the needle on most tasks | Acknowledge in the report; this is a plumbing-validation run, not a result claim |
| `--yes-always` issues in aider (per upstream bug) | Not relevant since we're using mini-swe-agent |

## Iteration log

- _initial_: hypothesised aider + OpenRouter.
- _research round 1_: verified aider's `--read` / `--message` flags and OpenRouter env var.
- _research round 2_: SWE-agent team recommends mini-swe-agent as the default. mini-swe-agent has linear messages, native LiteLLM, free cost reporting.
- _decision_: pivot to mini-swe-agent. Aider becomes plan-B.
- _impl_: built `mini_swe_runner.py` (static + dynamic injection modes), 2 eval-task fixtures, sweep script with isolated tmp repos per cell, dry-run mode via `DeterministicModel`. All 31 tests pass (2 live skipif).
- _verified offline_: full sweep `--dry-run` runs through baseline_a / baseline_b / hybrid_retrieval on both tasks; chunks correctly injected, costs reported, repos isolated, grading via `pytest` working.

## How to actually run it (when you have a key)

```bash
export OPENROUTER_API_KEY=sk-or-...
python scripts/run_harness_sweep.py \
  --models 'openrouter/anthropic/claude-haiku-4.5' 'openrouter/anthropic/claude-sonnet-4.6' \
  --policies baseline_a baseline_b hybrid_retrieval \
  --tasks eval_tasks/fizzbuzz_off_by_one eval_tasks/regex_backref \
  --runs 1 \
  --cost-limit 0.25 \
  --out runs/sweep_$(date +%s).csv
```

The `--cost-limit 0.25` per-task cap means the worst case for the matrix above (2 models × 3 policies × 2 tasks = 12 cells) is **~$3 total**. Each cell uses a fresh tmpdir copy of the task repo; nothing in `eval_tasks/` is mutated. Add `--dynamic` to switch to mid-trajectory injection mode for System 3.

For a smaller initial smoke check, just run on one cell:

```bash
python scripts/run_harness_sweep.py \
  --models 'openrouter/anthropic/claude-haiku-4.5' \
  --policies hybrid_retrieval \
  --tasks eval_tasks/fizzbuzz_off_by_one \
  --cost-limit 0.10
```
