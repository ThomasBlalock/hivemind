# Glossary

- **Skill** — a self-contained instruction/tool-schema unit. Includes Anthropic Skills, Cursor rules, OpenHands microagents, Continue prompts. See [skills_corpus/README.md](skills_corpus/README.md).
- **Skill Retrieval Augmentation (SRA)** — retrieving skills at runtime instead of preloading all of them. HiveMind is an SRA system.
- **Injection point** — the place in the agent's prompt where retrieved context is spliced in. See [agent_harness/integration.md](agent_harness/integration.md).
- **Injection policy** — the algorithm that decides what to inject. See [context_injection/README.md](context_injection/README.md).
- **Synthesis call** — one invocation of `POST /synthesize`. The unit of measurement for latency and cost.
- **Token budget** — the max tokens an injection policy may emit per call.
- **Baseline A / B** — no-skills baseline and naive-keyword-trigger baseline; see [../todo/plan.md](../todo/plan.md) Phase 4.
- **Trajectory** — one full agent run on one task, from first turn to final outcome.
