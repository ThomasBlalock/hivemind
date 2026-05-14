# API

Schema and rationale live in [../agent_harness/integration.md](../agent_harness/integration.md). This doc covers the surrounding endpoints and operational concerns.

## Endpoints

- `POST /synthesize` — main call (see linked schema)
- `POST /feedback` — outcome reporting; optional for clients
- `GET /policies` — list active injection policies and their versions
- `GET /healthz`, `GET /metrics` — standard ops

## Versioning

Policies are versioned (`hybrid_retrieval@v1`). Clients may pin; the default is the current production policy. Retired policies remain queryable for 90 days so prior runs stay reproducible.

## Auth

Public read of `GET /policies`. `POST /synthesize` and `POST /feedback` require an API key (rate-limited per key). Anonymous tier for offline eval reproductions.
