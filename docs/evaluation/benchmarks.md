# Benchmarks

## Primary

- **SWE-bench Verified** — 500 high-confidence real GitHub issues. Standard for coding agents.
- **SWE-bench Lite** — 300-task subset. Use this for fast iteration; promote to Verified before publishing numbers.

## Secondary

- **Aider polyglot** — multi-language code edits. Cheaper than SWE-bench, broader language coverage.
- **Terminal-Bench** — heavier tool-use; useful once non-code skills enter the corpus.

## Held-out splits

Reserve 20% of any suite we optimize against (notably [System 2](../context_injection/02_dspy_compiled_skills.md)) as a held-out set. Split by task *family* (e.g. repository), not random, to detect overfitting.

See [inspect_ai.md](inspect_ai.md) for runner config; see [../../todo/plan.md](../../todo/plan.md) Phase 4 for the baselines using these.
