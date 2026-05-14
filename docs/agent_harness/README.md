# Agent harness integration

We integrate HiveMind into two harnesses:

- [openhands.md](openhands.md) — primary; largest open user base
- [hermes.md](hermes.md) — named in [../../CLAUDE.md](../../CLAUDE.md) as the integration target

Both harnesses expose a single [injection point](integration.md) that calls our service. The eval harness ([../evaluation/README.md](../evaluation/README.md)) drives the agent harness on benchmark tasks.

## Why two

OpenHands gives us scale (a real test of cross-session network effects). Hermes is the marquee adoption story. Both should reach the same `POST /synthesize` API unchanged.
