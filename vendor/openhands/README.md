# vendor/openhands

Placeholder for a pinned OpenHands vendor patch (see [../../docs/agent_harness/openhands.md](../../docs/agent_harness/openhands.md)).

The HiveMind side of the integration is implemented in
[`src/hivemind/harness/adapter.py`](../../src/hivemind/harness/adapter.py) — either
`InProcessAdapter` (run HiveMind in the same Python process as OpenHands) or
`HTTPAdapter` (call the remote `/synthesize` endpoint).

## When you vendor for real

1. Pin a recent OpenHands commit:
   `git submodule add https://github.com/All-Hands-AI/OpenHands vendor/openhands/upstream`
2. Apply a patch to replace the microagent loader's keyword match with a call
   to `HTTPAdapter().inject(...)`.
3. Patch lives at `patches/0001-hivemind-injection.patch` so it can be
   reapplied when bumping the pin.

Deliberately left unvendored to keep this repo small; see plan Phase 2.
