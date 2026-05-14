# Hermes integration

Hermes is named in [../../CLAUDE.md](../../CLAUDE.md) as the integration target — the proof that an external project will adopt our endpoint.

## Plan

Mirror the [OpenHands integration](openhands.md): replace whatever skills-loading mechanism Hermes uses with a call to `POST /synthesize`. Same [API contract](integration.md), no harness-specific branches in HiveMind.

## Open questions

- Does Hermes load skills per-session or per-turn? Per-turn is the more interesting integration (enables [System 3](../context_injection/03_online_bandit.md) mid-trajectory injection).
- Hermes's prompt assembly order — we want to insert before tool definitions, after the system prompt. Verify against current `main` when Phase 2 begins.

TBD: validate against current Hermes `main` once we start Phase 2.
