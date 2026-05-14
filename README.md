# HiveMind: Dynamic Context Optimization Hub

**Stop statically stuffing your LLM's context window with skills.** HiveMind is an open-source research initiative and production-grade runtime engine that dynamically injects the mathematically optimal sequence of skills, instructions, and tools into an agent's reasoning stream. 

The goal: **Unlock frontier-model performance from mid-tier models at half the latency and token cost.**

---

## 🧠 The Core Insight: We Can Do Better Than Static Skills

There exists a sequence of tokens to inject into your context that will optimally improve its performance. This optimal sequence depends on the task, the model, and the other tokens in the LLM's context. If you are building AI agents today, your capability pipeline likely relies on naive text injection. You write static Markdown files for "skills" or "system prompts" and insert them using basic keyword triggers or brute-force system messages.

This approach creates critical structural bottlenecks:
1. **Context Dilution:** Bloating the attention window degrades reasoning precision while driving up token costs and Time-to-First-Token (TTFT) latency quadratically.
2. **Sub-Optimality:** Static skill files are general rather than tailored to specific tasks and conversational context. This leaves significant room to optimize.
3. **Isolated Workflows:** Every developer curates their own rigid, siloed set of instructions. There is no global feedback loop to learn which context sequences actually yield successful multi-turn executions.

---

## Enter HiveMind

HiveMind treats **context injection as a dynamic, highly optimizable search and synthesis problem.** Instead of hardcoding a massive block of system instructions, your agent harness queries the HiveMind runtime middleware before or during an inference turn. HiveMind analyzes the active conversation state, RAGs against a highly curated, secure corpus of skills, and serves an optimized token payload designed specifically to maximize downstream task success.

### Why Developers & Researchers Will Use HiveMind
* **The Cost-Performance Frontier:** By dynamically scoping context, you can strip out irrelevant tokens. I am iteratively benchmarking context-injection policies until mid-tier models match the coding task success rates of unoptimized frontier models.
* **Plug-and-Play Extensibility:** Drop bloated static prompts from your application code. Integrate our lightweight agent harness middleware (meant to be compatible with frameworks like Hermes Agent) to instantly access a globally optimized skills library.
* **Autonomous Evolution:** HiveMind is designed to close the loop. By mapping task inputs, injected context, and end-state evaluations, it will continuously train to improve global context injection over time.

---

## 🛡️ Production-Grade Security & Constraints

Injecting external context into dynamic execution loops introduces unique attack surfaces. HiveMind is engineered with stringent operational boundaries:
* **Audited Corpus:** Every skill added to the global repository undergoes strict automated static analysis and sandboxed prompt-injection tests to prevent malicious instruction overrides.
* **Publicly Verifiable Infrastructure:** Built on transparent, auditable release pipelines so application developers can trust the runtime payload unconditionally.
* **Strict Latency Budgets:** Retrieval and compilation policies are engineered using highly optimized retrieval engines and lightweight synthesis models to guarantee negligible TTFT overhead.

---

## 🗺️ Project Roadmap & Architecture

We are building in transparent, rigorous phases. Check our active progress and contribute to specific modules below.

### Architectural Tiers
* **System 1 (Hybrid Retrieval):** Advanced vector + BM25 sparse indexing over atomic skill files to ensure absolute keyword retrieval accuracy.
* **System 2 (DSPy Compiled Policies):** Programmatic prompt compilation to discover model-specific structural optimizations.
* **System 3 (Online Bandits):** Real-time exploration/exploitation routing based on historical task reward telemetry.

---

## 📖 Documentation & Navigation Matrix

The complete system architecture, evaluation results, and module designs live under `docs/`. To track active engineering execution tasks, check `todo/plan.md`.

If you are looking to contribute or understand a specific subsystem, jump directly to the relevant resource:

| If you're modifying... | Look at this first |
|---|---|
| **Project-wide architecture or data flow** | `docs/architecture.md` |
| **The evaluation harness** (Inspect AI benchmarks, cost metrics) | `docs/evaluation/README.md` |
| **Agent harness integration** (OpenHands, Hermes, API contracts) | `docs/agent_harness/README.md` |
| **The skills corpus** (sources, ingestion pipelines, security audits) | `docs/skills_corpus/README.md` |
| **A context injection policy** | `docs/context_injection/README.md` |
| **The basic hybrid-retrieval policy (System 1)** | `docs/context_injection/01_hybrid_retrieval.md` |
| **The DSPy-compiled policy (System 2)** | `docs/context_injection/02_dspy_compiled_skills.md` |
| **The online-bandit policy (System 3)** | `docs/context_injection/03_online_bandit.md` |
| **The serving API or release process** | `docs/serving/README.md` |
| **Terminology you don't recognize** | `docs/glossary.md` |
| **The phased implementation plan** | `todo/plan.md` |
| **The master documentation index** | `docs/README.md` |

---

## 🤝 Get Involved

Whether you are an AI researcher passionate about attention mechanics, a systems engineer optimizing RAG pipelines, or an agent developer tired of managing prompt files, HiveMind welcomes your contributions. Check out our evaluation benchmarks to see our current performance targets, or pick up an issue from the `todo/plan.md` ledger.



# HiveMind

Dynamic Context Optimization Hub — a Skill Retrieval Augmentation service for agent harnesses.

> Vision: [CLAUDE.md](CLAUDE.md)
> Design docs: [docs/](docs/README.md)
> Plan with checkboxes: [todo/plan.md](todo/plan.md)

## Quickstart (offline / scaffolded mode)

```bash
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"

# Build the toy corpus from corpus/skills/*.md
hivemind corpus build

# Run the API
hivemind serve

# In another shell
curl -s localhost:8000/healthz
```

Out of the box, embeddings + rerankers are **stubbed** (deterministic hash-based) so nothing makes a network call. Install the `live` extra and set `VOYAGE_API_KEY` / `COHERE_API_KEY` to switch in real backends — see [docs/serving/README.md](docs/serving/README.md).

## Tests

```bash
uv pip install -e ".[dev]"
pytest
```

## What lives where

```
src/hivemind/
  corpus/         # Ingestion, schema, security audit, index
  policies/       # Injection policies (baselines + 3 systems)
  api/            # FastAPI service
  eval/           # Inspect AI task stubs + report
  harness/        # Adapter interface + fake harness for testing
  embeddings.py   # Voyage / stub embedder
  reranker.py     # Voyage / stub reranker
corpus/skills/    # Toy skill source files (markdown + frontmatter)
docs/             # Design docs (read these before editing code)
todo/plan.md      # Implementation status
```
