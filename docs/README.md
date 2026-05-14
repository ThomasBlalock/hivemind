# HiveMind Documentation

Project vision: [../CLAUDE.md](../CLAUDE.md)
Implementation plan: [../todo/plan.md](../todo/plan.md)

## Map

- [Overview](overview.md) — one-page summary of problem, vision, end-state
- [Architecture](architecture.md) — components and data flow
- [Glossary](glossary.md) — recurring terms

### Subsystems

- [Evaluation harness](evaluation/README.md) — Inspect AI + SWE-bench + cost tracking
- [Agent harness integration](agent_harness/README.md) — OpenHands, Hermes
- [Skills corpus](skills_corpus/README.md) — sources, ingestion, security audit
- [Context injection systems](context_injection/README.md) — the research target
- [Serving layer](serving/README.md) — the public endpoint

## Conventions

- Each doc is short (target < 100 lines). If a doc grows, split it.
- Cross-link with relative paths. Reference code with `src/...` paths.
- Use "TBD" for known unknowns; "TODO" must reference a line in [../todo/plan.md](../todo/plan.md).
