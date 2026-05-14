# OpenHands integration

OpenHands already has "microagents" — markdown files loaded into context on trigger. We replace the trigger logic with a call to `POST /synthesize`.

## Touchpoints

- `openhands/microagent/registry.py` (verify path against pinned version) — replace keyword match with an HTTP call.
- Request payload: event stream, target model id, remaining token budget.
- Response payload: list of `{content, position}` chunks to splice in. See [integration.md](integration.md).

## Fork strategy

Vendor a pinned OpenHands version under `vendor/openhands/` with a thin patch. Avoid an upstream fork until the API is stable; revisit once Phase 5 has a clear winner.

## Trigger compatibility

Existing microagent trigger keywords are preserved in the [skills corpus](../skills_corpus/ingestion.md) schema so baseline B (naive keyword injection) is reproducible from the same data.
