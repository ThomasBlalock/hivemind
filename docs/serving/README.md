# Serving layer

A FastAPI service exposing the [injection-point API](../agent_harness/integration.md).

- [api.md](api.md) — full API spec

## Non-functional targets

- p50 latency < 200 ms (otherwise we eat into the foundation model's budget)
- p95 latency < 500 ms
- Per-call cost < 5% of the downstream foundation-model call

## Release process

Reproducible builds, sigstore signatures, SLSA provenance attestations. Container image signed. Source code publicly auditable per [../../CLAUDE.md](../../CLAUDE.md) constraints.
