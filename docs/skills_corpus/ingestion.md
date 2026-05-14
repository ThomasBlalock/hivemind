# Skill ingestion

Every source normalizes to one schema in `src/corpus/skills.jsonl`.

## Schema

```
{
  "id": "git-bisect",
  "title": "Use git bisect to find a regression",
  "description": "When the user reports a regression with a known good commit...",
  "triggers": ["bisect", "regression", "broken commit"],   // original keyword triggers, preserved for baseline B
  "body": "...",                                            // full skill content
  "source": "anthropics/skills@<commit-sha>",
  "tokens": 412,                                            // counted with tiktoken/cl100k for budgeting
  "audit_status": "passed"                                  // see security_audit.md
}
```

## Pipeline (`src/corpus/ingest.py`)

1. Pull each source at a pinned commit.
2. Normalize to the schema above.
3. Run the [security audit](security_audit.md). Drop on failure.
4. Embed `title + description + body[:200_tokens]` with `voyage-3`; store vectors in LanceDB.
5. Build a BM25 index over `title + description + triggers + body`.

Embedding and BM25 indexes feed [System 1](../context_injection/01_hybrid_retrieval.md). Distilled per-model variants from [System 2](../context_injection/02_dspy_compiled_skills.md) get appended to the schema as a sub-table.
