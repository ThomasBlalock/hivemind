# Skills corpus

A curated, audited, normalized set of skills served by HiveMind.

- [sources.md](sources.md) — where we pull from
- [ingestion.md](ingestion.md) — normalization pipeline + storage schema
- [security_audit.md](security_audit.md) — required gate before any skill enters the corpus

The corpus is consumed by every [context injection system](../context_injection/README.md). Versioned at the commit level so any served chunk is reproducible from its `source_sha`.

## Target size

200–500 skills in the initial corpus. Big enough that retrieval matters; small enough that human audit is tractable.
