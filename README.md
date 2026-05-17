# HiveMind: Dynamic Context Optimization Hub

**Stop statically stuffing your LLM's context window with skills.** HiveMind is an open-source skills hub observer that dynamically injects the mathematically optimal sequence of skills, instructions, and tools into an agent's reasoning stream. 

The goal: **Unlock frontier-model performance from mid-tier models at half the latency and token cost.**

---


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

---

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

---

## We Can Do Better Than Static Skills

There exists a sequence of tokens to inject into your context that will optimally improve its performance. This optimal sequence depends on the task, the model, and the other tokens in the LLM's context. If you are building AI agents today, your capability pipeline likely relies on naive text injection. You write static Markdown files for "skills" or "system prompts" and insert them using basic keyword triggers or brute-force system messages.

This approach creates critical structural bottlenecks:
1. **Context Dilution:** Bloating the attention window degrades reasoning precision while driving up token costs and Time-to-First-Token (TTFT) latency quadratically.
2. **Sub-Optimality:** Static skill files are general rather than tailored to specific tasks and conversational context. This leaves significant room to optimize.
3. **Isolated Workflows:** Every developer curates their own rigid, siloed set of instructions. There is no global feedback loop to learn which context sequences actually yield successful multi-turn executions.

---

## Enter HiveMind

HiveMind treats **context injection as a dynamic, highly optimizable search and synthesis problem.** Instead of hardcoding a massive block of system instructions, your agent harness queries the HiveMind runtime middleware before or during an inference turn. HiveMind analyzes the active conversation state, RAGs against a highly curated, secure corpus of skills, and serves an optimized token payload designed specifically to maximize downstream task success.

## Why This is Useful
* **The Cost-Performance Frontier:** By dynamically scoping context, you can strip out irrelevant tokens. I am iteratively benchmarking context-injection policies until mid-tier models match the coding task success rates of unoptimized frontier models.
* **Plug-and-Play Extensibility:** Drop bloated static prompts from your application code. Integrate our lightweight agent harness middleware (meant to be compatible with frameworks like Hermes Agent) to instantly access a globally optimized skills library.
* **Autonomous Evolution:** HiveMind is designed to close the loop. By mapping task inputs, injected context, and end-state evaluations, it will continuously train to improve global context injection over time.

---

## Security & Constraints

Injecting external context into dynamic execution loops introduces unique attack surfaces. HiveMind is engineered with stringent operational boundaries:
* **Audited Corpus:** Every skill added to the global repository undergoes strict automated static analysis and sandboxed prompt-injection tests to prevent malicious instruction overrides.
* **Publicly Verifiable Infrastructure:** Built on transparent, auditable release pipelines so application developers can trust the runtime payload unconditionally.
* **Strict Latency Budgets:** Retrieval and compilation policies are engineered using highly optimized retrieval engines and lightweight synthesis models to guarantee negligible TTFT overhead.

---

## Get Involved

Email me at blalockthomasm@gmail.com
