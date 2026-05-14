# Cost tracking via LiteLLM

Every model call goes through a LiteLLM proxy so cost is normalized across providers and logged in one place.

## Setup

- `proxy_config.yaml` declares models with per-token cost.
- Inspect AI points at `http://localhost:4000` instead of the provider directly.
- LiteLLM writes a row per request to sqlite. We join against Inspect logs by request id.

## What we report

`src/eval/report.py` produces:

- cost-per-task (USD)
- p50/p95 synthesis latency
- success rate
- tokens injected per synthesis call

These feed the perf-vs-cost graph that is HiveMind's end-state deliverable (see [../overview.md](../overview.md)).
