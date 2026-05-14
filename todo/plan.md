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
- [ ] Scaffold `src/eval/` with an Inspect AI task stub
- [ ] Reproduce a published SWE-bench-Lite number for one model

## Phase 2 — Agent harness integration

- [x] [`docs/agent_harness/README.md`](../docs/agent_harness/README.md)
- [x] [`docs/agent_harness/openhands.md`](../docs/agent_harness/openhands.md)
- [x] [`docs/agent_harness/hermes.md`](../docs/agent_harness/hermes.md)
- [x] [`docs/agent_harness/integration.md`](../docs/agent_harness/integration.md) — the injection-point contract
- [ ] Vendor OpenHands at a pinned version with the injection hook
- [ ] Mirror into Hermes

## Phase 3 — Skills corpus

- [x] [`docs/skills_corpus/README.md`](../docs/skills_corpus/README.md)
- [x] [`docs/skills_corpus/sources.md`](../docs/skills_corpus/sources.md)
- [x] [`docs/skills_corpus/ingestion.md`](../docs/skills_corpus/ingestion.md)
- [x] [`docs/skills_corpus/security_audit.md`](../docs/skills_corpus/security_audit.md)
- [ ] Implement `src/corpus/ingest.py`; produce `skills.jsonl`

## Phase 4 — Baselines

- [ ] Baseline A: no skills injected
- [ ] Baseline B: naive keyword-trigger injection (current state-of-practice)
- [ ] Record success rate, cost, p50/p95 latency per task

## Phase 5 — Context injection systems

Each system has its own doc under [`docs/context_injection/`](../docs/context_injection/README.md). Three systems this iteration, escalating in complexity and promise.

**Seed for system 1 (basic):** replace literal keyword matching with semantic + lexical hybrid retrieval (BM25 + dense embeddings) followed by a cross-encoder reranker, packed under a token budget. Same input/output shape as the keyword system; learned components are all off-the-shelf. Full design in [`01_hybrid_retrieval.md`](../docs/context_injection/01_hybrid_retrieval.md) — design that one carefully when getting to it.

- [x] [`docs/context_injection/README.md`](../docs/context_injection/README.md) — comparison matrix
- [x] [`docs/context_injection/01_hybrid_retrieval.md`](../docs/context_injection/01_hybrid_retrieval.md) — System 1 (basic)
- [x] [`docs/context_injection/02_dspy_compiled_skills.md`](../docs/context_injection/02_dspy_compiled_skills.md) — System 2 (medium)
- [x] [`docs/context_injection/03_online_bandit.md`](../docs/context_injection/03_online_bandit.md) — System 3 (advanced)
- [ ] Implement system 1 behind the `/synthesize` API
- [ ] Implement system 2 (depends on Phase 1 being solid)
- [ ] Implement system 3 (depends on system 2 as warm start)

## Phase 6 — Comparison & iteration

- [ ] Run baselines A, B + systems 1, 2, 3 through the eval suite
- [ ] Produce the perf-vs-cost graph called for in [`../CLAUDE.md`](../CLAUDE.md)
- [ ] Iterate until a mid-tier model + injection matches a top-tier model bare

## Phase 7 — Serving layer

- [x] [`docs/serving/README.md`](../docs/serving/README.md)
- [x] [`docs/serving/api.md`](../docs/serving/api.md)
- [ ] FastAPI service in `src/api/` exposing `POST /synthesize`, `POST /feedback`
- [ ] Reproducible signed releases (sigstore + SLSA)

---

## Constraints (from CLAUDE.md, enforced cross-cutting)

- Every served skill passes [security audit](../docs/skills_corpus/security_audit.md).
- p50 synthesis latency < 200 ms; p95 < 500 ms.
- Per-call cost < 5% of the downstream foundation-model call.
- Public, auditable, signed releases.
