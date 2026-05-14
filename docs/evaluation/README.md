# Evaluation harness

Goal: produce repeatable scores for (agent × model × injection policy) on coding tasks, including cost.

## Pieces

- [benchmarks.md](benchmarks.md) — task suites
- [inspect_ai.md](inspect_ai.md) — runner of choice
- [cost_tracking.md](cost_tracking.md) — LiteLLM proxy for normalized cost

## Why these tools

Inspect AI gives us logs, sandbox runners, and a viewer for free — we don't build them. SWE-bench Verified is the standard for coding-agent eval. LiteLLM normalizes cost across providers in one place.

## Outputs the rest of the project depends on

- A reproducible command: `inspect eval src/eval/swe_bench_lite.py --model <id> -T policy=<id>`.
- A cost-per-task report at `runs/<timestamp>/cost.csv`.

The eval harness drives the [agent harness](../agent_harness/README.md), which calls the [injection policy](../context_injection/README.md) being studied.
