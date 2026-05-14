# Context injection systems

The research target. Each system implements the same [API contract](../agent_harness/integration.md) so the eval harness can swap them as a parameter.

## Systems (this iteration)

| # | Name | Doc | Idea | Promise | Build cost |
|---|---|---|---|---|---|
| 1 | Hybrid Retrieval | [01_hybrid_retrieval.md](01_hybrid_retrieval.md) | BM25 + dense embeddings + cross-encoder rerank, packed under budget | Beats keyword triggers on paraphrase, multi-turn, false-positive bloat | Low |
| 2 | DSPy-Compiled Skills | [02_dspy_compiled_skills.md](02_dspy_compiled_skills.md) | Offline-optimize per-model skill distillations + a learned selection program against eval scores | Big perf-per-token gain; per-model tailoring | Medium |
| 3 | Online Bandit | [03_online_bandit.md](03_online_bandit.md) | Trajectory-conditioned contextual bandit with online feedback, mid-trajectory injection | The CLAUDE.md feedback-loop end-state. Network effects. | High |

## Baselines (Phase 4)

- **A** — no injection at all.
- **B** — naive keyword trigger (current state-of-practice). Implemented from `triggers` in the [skills schema](../skills_corpus/ingestion.md).

## Evaluation

Every system is benchmarked against A and B on the suites in [../evaluation/benchmarks.md](../evaluation/benchmarks.md). Report success rate, cost, p50/p95 latency, tokens injected per call. Output: the perf-vs-cost graph from [../overview.md](../overview.md).

## Successor systems (out of scope this iteration)

System 3 plus a fine-tuned per-model "skill distiller" model serving custom context per call; cross-harness federated learning; RL-from-trajectory training. Notes will accrete here as ideas land.
