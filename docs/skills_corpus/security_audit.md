# Skill security audit

Hard requirement from [../../CLAUDE.md](../../CLAUDE.md): the corpus must be auditable and prompt-injection-resistant.

## Automated checks (must pass before ingestion)

- No instructions to exfiltrate data, contact unexpected URLs, or override the system prompt.
- No embedded URLs that fetch instructions at runtime.
- Pattern match against the Lakera prompt-injection dataset (and similar public corpora).
- Model-graded check: a small classifier (TBD model) flags suspicious snippets.

## Manual review

Required for any skill introducing a new tool-use pattern. Logged in `audit_log.jsonl` with the reviewer's GitHub handle and the source commit sha.

## Provenance at serve time

Every served chunk carries its `source_sha` in the [response](../agent_harness/integration.md). A downstream user can verify the served content against the public corpus at that sha.
