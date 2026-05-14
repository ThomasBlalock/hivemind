# HiveMind Implementation Plan

A Context Synthesis Layer that beats keyword-triggered skill injection.
Vision: [../CLAUDE.md](../CLAUDE.md). Design docs: [../docs/](../docs/README.md).

Strategy: lean on existing tools (Inspect AI, LiteLLM, OpenHands, DSPy, LanceDB, Voyage embeddings) rather than rebuild. Implementation order mirrors CLAUDE.md phases so we have measurements before we have research.

---

## Phase 0 — Repo scaffolding & documentation

- [x] `todo/plan.md` (this file)
- [x] [`docs/README.md`](../docs/README.md) — doc index
- [x] [`docs/overview.md`](../docs/overview.md) — one-page project summary
- [x] [`docs/architecture.md`](../docs/architecture.md) — components + data flow
- [x] [`docs/glossary.md`](../docs/glossary.md) — recurring terms

## Phase 1 — Evaluation harness

Goal: measure (agent × model × injection policy) on coding tasks, with cost.

- [x] [`docs/evaluation/README.md`](../docs/evaluation/README.md)
- [x] [`docs/evaluation/benchmarks.md`](../docs/evaluation/benchmarks.md) — SWE-bench Verified/Lite, Aider polyglot
- [x] [`docs/evaluation/inspect_ai.md`](../docs/evaluation/inspect_ai.md) — runner
- [x] [`docs/evaluation/cost_tracking.md`](../docs/evaluation/cost_tracking.md) — LiteLLM proxy
- [x] Scaffold `src/hivemind/eval/` with Inspect AI task stubs (`swe_bench_lite.py`, `aider_polyglot.py`, `policy_adapter.py`, `report.py`, `litellm_proxy_config.yaml`)
- [ ] **Deferred (needs live API spend):** reproduce a published SWE-bench-Lite number for one model

## Phase 2 — Agent harness integration

- [x] [`docs/agent_harness/README.md`](../docs/agent_harness/README.md)
- [x] [`docs/agent_harness/openhands.md`](../docs/agent_harness/openhands.md)
- [x] [`docs/agent_harness/hermes.md`](../docs/agent_harness/hermes.md)
- [x] [`docs/agent_harness/integration.md`](../docs/agent_harness/integration.md) — the injection-point contract
- [x] Adapter implementation: `InProcessAdapter` + `HTTPAdapter` in `src/hivemind/harness/adapter.py`
- [x] `FakeHarness` end-to-end test driver
- [ ] **Deferred:** vendor a real OpenHands pin + apply the injection patch
- [ ] **Deferred:** mirror into Hermes (upstream not yet identified)

## Phase 3 — Skills corpus

- [x] [`docs/skills_corpus/README.md`](../docs/skills_corpus/README.md)
- [x] [`docs/skills_corpus/sources.md`](../docs/skills_corpus/sources.md)
- [x] [`docs/skills_corpus/ingestion.md`](../docs/skills_corpus/ingestion.md)
- [x] [`docs/skills_corpus/security_audit.md`](../docs/skills_corpus/security_audit.md)
- [x] Implement ingestion pipeline (`src/hivemind/corpus/{schema,security_audit,ingest,index}.py`) and toy corpus (3 skills under `corpus/skills/`)
- [x] `hivemind corpus build` produces `corpus/skills.jsonl`
- [ ] **Deferred:** pull and audit a full 200–500 skill corpus from upstream sources

## Phase 4 — Baselines

- [x] Baseline A: implemented in `src/hivemind/policies/baseline.py` (`BaselineA`)
- [x] Baseline B: naive keyword-trigger injection (`BaselineB`)
- [ ] **Deferred (needs live API spend):** record success rate, cost, p50/p95 latency per task

## Phase 5 — Context injection systems

Each system has its own doc under [`docs/context_injection/`](../docs/context_injection/README.md). Three systems this iteration, escalating in complexity and promise.

**Seed for system 1 (basic):** replace literal keyword matching with semantic + lexical hybrid retrieval (BM25 + dense embeddings) followed by a cross-encoder reranker, packed under a token budget. Same input/output shape as the keyword system; learned components are all off-the-shelf. Full design in [`01_hybrid_retrieval.md`](../docs/context_injection/01_hybrid_retrieval.md) — design that one carefully when getting to it.

- [x] [`docs/context_injection/README.md`](../docs/context_injection/README.md) — comparison matrix
- [x] [`docs/context_injection/01_hybrid_retrieval.md`](../docs/context_injection/01_hybrid_retrieval.md) — System 1 (basic)
- [x] [`docs/context_injection/02_dspy_compiled_skills.md`](../docs/context_injection/02_dspy_compiled_skills.md) — System 2 (medium)
- [x] [`docs/context_injection/03_online_bandit.md`](../docs/context_injection/03_online_bandit.md) — System 3 (advanced)
- [x] Implement System 1 (`HybridRetrievalPolicy`) — full pipeline: query construction → BM25 + dense → RRF → rerank → threshold → budget pack
- [x] Implement System 2 scaffold (`DSPyCompiledPolicy`) — serves distilled bodies when artifacts exist; degrades to System 1 otherwise. Trainer skeleton in `dspy_train.py`.
- [x] Implement System 3 scaffold (`OnlineBanditPolicy`) — per-skill LinUCB over a hashed state featurization; `record_feedback` updates arms; warm-starts from System 2.
- [ ] **Deferred:** run System 2 offline optimization (needs Phase 1 live, DSPy install, funded LLM key)
- [ ] **Deferred:** accumulate online feedback for System 3 (needs real harness traffic)

## Phase 6 — Comparison & iteration

- [ ] **Deferred (needs live API spend):** run baselines A, B + Systems 1, 2, 3 through the eval suite
- [ ] **Deferred:** produce the perf-vs-cost graph called for in [`../CLAUDE.md`](../CLAUDE.md)
- [ ] **Deferred:** iterate until a mid-tier model + injection matches a top-tier model bare

## Phase 7 — Serving layer

- [x] [`docs/serving/README.md`](../docs/serving/README.md)
- [x] [`docs/serving/api.md`](../docs/serving/api.md)
- [x] FastAPI service in `src/hivemind/api/` exposing `POST /synthesize`, `POST /feedback`, `GET /policies`, `GET /healthz`, `GET /metrics`
- [x] `hivemind serve` CLI command
- [ ] **Deferred:** reproducible signed releases (sigstore + SLSA)

---

## Constraints (from CLAUDE.md, enforced cross-cutting)

- Every served skill passes [security audit](../docs/skills_corpus/security_audit.md).
- p50 synthesis latency < 200 ms; p95 < 500 ms.
- Per-call cost < 5% of the downstream foundation-model call.
- Public, auditable, signed releases.

---

## What's deferred and why

Items marked **Deferred** above were intentionally not run in this build session — they either need live API spend, a real harness to vendor, or external upstream identification. Each is annotated inline.

The shortest path to lighting them up:

1. Install `.[live]`, export `VOYAGE_API_KEY` + `ANTHROPIC_API_KEY`, switch `HIVEMIND_EMBEDDER=voyage` and `HIVEMIND_RERANKER=voyage`. Re-run `pytest` to confirm; nothing should break.
2. Install `.[eval]`, run `inspect eval -m src/hivemind/eval/swe_bench_lite.py --model anthropic/claude-sonnet-4-6 -T policy=baseline_b`. Confirm one task completes end-to-end before scaling up.
3. Real corpus pull: write a `src/hivemind/corpus/sources/` adapter per source and feed `ingest_directory` from there. Audit gate is already in place.
4. Vendor OpenHands once the upstream API is steady; the integration point is `HTTPAdapter.inject` and the patch should call it from the microagent loader.
