# vendor/hermes

Placeholder for a Hermes vendor patch (see [../../docs/agent_harness/hermes.md](../../docs/agent_harness/hermes.md)).

The CLAUDE.md project vision names "Hermes" as a target harness without a
canonical repo URL; verify the right upstream before vendoring. Likely
candidates to check:

- `NousResearch/Hermes-*`
- a fresh "Hermes" agent harness in the SRA / coding-agent space

Same integration pattern as [vendor/openhands](../openhands/README.md): use
`HTTPAdapter` from `src/hivemind/harness/adapter.py`.
