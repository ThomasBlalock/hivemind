# Inspect AI runner

Why Inspect AI: built-in cost/token logging, a log viewer (`inspect view`), sandbox runners suitable for SWE-bench, and a clean Python task DSL.

## Planned layout

- `src/eval/swe_bench_lite.py` — wraps the official SWE-bench harness as an Inspect task
- `src/eval/aider_polyglot.py` — same shape
- `src/eval/policies/` — adapter for each injection policy, exposing the same `synthesize(conversation, budget) -> chunks` interface so eval runs can swap policies as a task parameter

## Running

```bash
uv run inspect eval src/eval/swe_bench_lite.py \
  --model anthropic/claude-sonnet-4-6 \
  -T policy=baseline_b
```

`policy=baseline_a` (no skills), `baseline_b` (keyword), `hybrid_retrieval`, `dspy_compiled`, `online_bandit`.

Cross-refs: [cost_tracking.md](cost_tracking.md), [../agent_harness/integration.md](../agent_harness/integration.md).
