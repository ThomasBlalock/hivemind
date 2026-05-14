# Skill sources

## Implemented adapters

| Source key | Repo | Adapter | Pinned commit |
|---|---|---|---|
| `anthropic_skills` | [anthropics/skills](https://github.com/anthropics/skills) | `src/hivemind/corpus/sources/anthropic_skills.py` | `f458cee31a7577a47ba0c9a101976fa599385174` |
| `openhands_microagents` | [OpenHands/OpenHands](https://github.com/OpenHands/OpenHands) | `src/hivemind/corpus/sources/openhands_microagents.py` | `e7b5e3079592a1cffb3fb64b8e0813b007ebbb2f` |

Run `hivemind corpus pull` to materialize skill markdown files; `hivemind corpus
build` then ingests them through the security audit into `skills.jsonl`. Audit
results land in `corpus/audit_log.jsonl` (gitignored).

The adapters use the GitHub Contents API via plain `urllib` — no `gh` CLI
dependency. Unauthenticated rate limits (60/hr) are adequate at our scale.

## Candidate future sources

| Source | Format | Notes |
|---|---|---|
| `awesome-claude-skills` (community) | mixed | Filter by stars/activity before audit |
| Cursor `.cursorrules` (curated lists) | plain md | Convert to Skills frontmatter in ingestion |
| Continue.dev `.prompts` | yaml + md | Convert |

Target seed: 200–500 skills. See [ingestion.md](ingestion.md) for the normalization step and [security_audit.md](security_audit.md) for the audit gate.

## Adding a new adapter

1. Subclass `SourceAdapter` in a new file under `src/hivemind/corpus/sources/`.
2. Pin a specific commit sha (don't track `main`).
3. Implement `pull(limit) -> list[NormalizedSkill]`.
4. Register it in `src/hivemind/corpus/sources/__init__.py`.
5. Add fixtures under `tests/fixtures/gh_*.json` and a test that monkey-patches
   `hivemind.corpus.sources.base.fetch_json` to return them — tests **must
   not** hit GitHub.
