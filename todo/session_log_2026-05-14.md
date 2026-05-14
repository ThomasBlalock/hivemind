# Autonomous session log — 2026-05-14

Executed `todo/autonomous_session_plan.md` in the prescribed order.
Starting state: commit `6340ef0` — 31 tests pass / 2 skip, 3 toy skills, 2 eval tasks.

## What shipped

All four options completed in full and committed to `main`.

| Order | Option | Commit | Lines | Notes |
|---|---|---|---|---|
| 1st | 4 — Results dashboard + reporting | `87dd439` | +803/-28 | `report.py` (load_sweep_csv, aggregate w/ bootstrap CI, markdown_report, perf_vs_cost_chart), `scripts/{build_report,synthesize_sweep_csv}.py`, 5 tests, matplotlib added to `[dev]`. |
| 2nd | 3 — Real DSPy programs for System 2 | `eb9aec0` | +736/-51 | `dspy_programs.py` (Distiller/Selector/Orderer), real `dspy_train.py` with LM-budget cap, `hivemind dspy train [--dry-run]` CLI, extended `dspy_compiled.py` to consume selector + order_prior. 5 dspy tests gated on `pytest.importorskip("dspy")`. |
| 3rd | 1 — Real skills corpus adapters | `0a000b1` | +5939/-4 | `sources/` package with two adapters pinned to specific commits (`anthropic_skills@f458cee`, `openhands_microagents@e7b5e30`). `hivemind corpus pull` CLI, audit-log writes, mocked tests. **23 real skills pulled and committed** (22 audit-pass, 1 known false-positive logged in `PROVENANCE.md`). Toy corpus moved to `tests/fixtures/toy_skills/` to preserve the 3-skill unit-test contract. |
| 4th | 2 — More eval tasks | `24e4150` | +683/-0 | 12 new tasks across easy/medium/hard tiers, `eval_tasks/README.md` catalog, `tests/test_eval_tasks.py` that validates shape AND asserts each task's `test_cmd` fails on the unmodified repo (catches "I forgot to introduce the bug"). |

## Test counts

| Phase | Pass | Skip | Collected |
|---|---:|---:|---:|
| Session start | 31 | 2 | 33 |
| After Option 4 | 36 | 2 | 38 |
| After Option 3 | 41 | 2 | 43 |
| After Option 1 | 46 | 2 | 48 |
| After Option 2 | 74 | 2 | 76 |

`ruff check src tests scripts` clean throughout.

## Constraints honored

- **No paid API calls.** All DSPy testing used `dspy.DummyLM`. Embedder / reranker
  stayed on deterministic stubs. The corpus pull touched only `api.github.com`
  (unauthenticated, within 60/hr).
- **No remote pushes.** Branch is 4 commits ahead of `origin/main`.
- **README.md untouched.** User has uncommitted local edits to it from before the
  session; deliberately left out of every commit.
- **CLAUDE.md body untouched.** Only the docs routing table picked up a new
  `docs/evaluation/reporting.md` row.
- Dependency pins not bumped.

## TODOs that surfaced during the session

1. **`claude-api` skill is dropped as an audit false-positive.** The
   `exfiltrate_secrets` regex hits "post the api key" inside a code example.
   The skill is benign instructional content — needs either a manual
   whitelist mechanism, or a tighter regex. Filed inline in
   `corpus/PROVENANCE.md`.

2. **`SkillSelector` synthetic labels are simplistic.** The trainer's
   selector reward compares against a hand-built positive/negative pair
   constructed from skill triggers. When DummyLM cycles answers that don't
   match the labels, `selector.json` ends up nearly empty — that's fine for
   the dry-run smoke test, but masks how lossy the real label set will be
   under a real LM. Worth revisiting before flipping to real reward.

3. **The reporting `pairwise` bootstrap CI uses integer-cast per-task means.**
   This is the right call when each task has one run per cell, but with
   `--runs >= 2` we lose granularity. Easy fix once we have real sweep data
   to see the impact.

4. **Eval-task validator uses `subprocess.run(test_cmd, shell=True)`.** That
   relies on `pytest` being on `PATH` from `sys.executable.parent`. Works on
   the current venv layout, but will need a more robust resolver if anyone
   runs the suite from a different env.

5. **OpenHands microagent extraction is shallow.** We pull from
   `.openhands/microagents/` and `.agents/skills/` only. That's 6 skills.
   The repo has more skill-shaped content under `microagents/` (top-level)
   and other documentation — worth a second look once we want corpus scale.

## Outstanding follow-ups for the user

- **Run the dry-run reporting pipeline once** to eyeball the chart shape:
  ```
  python scripts/synthesize_sweep_csv.py --out /tmp/fake.csv --runs 3
  python scripts/build_report.py /tmp/fake.csv --out-md /tmp/r.md --out-png /tmp/r.png
  ```
- **Decide whether to whitelist `claude-api`.** It's the biggest single skill
  in the upstream corpus and was dropped by the audit.
- **Run `pip install -e .[dspy,dev]` once** if you want the DSPy tests to
  actually run instead of skipping. (Currently they pass when dspy is
  installed; on a fresh clone they `pytest.importorskip`.)
- **Pick a real model + key for the next phase.** The full integration is
  blocked on a funded `OPENROUTER_API_KEY` to do real sweeps; everything
  upstream of that is now ready.

## Files added / modified summary

- New: `src/hivemind/corpus/sources/{__init__,base,anthropic_skills,openhands_microagents}.py`,
  `src/hivemind/corpus/pull.py`, `src/hivemind/policies/dspy_programs.py`,
  `scripts/{build_report,synthesize_sweep_csv}.py`,
  `tests/test_{report,dspy_programs,corpus_sources,eval_tasks}.py`,
  `tests/fixtures/{gh_*,toy_skills/}`,
  `eval_tasks/<12 new>/{task.yaml,repo/...}`,
  `docs/evaluation/reporting.md`,
  `corpus/PROVENANCE.md`,
  23 skill markdown files under `corpus/skills/`.
- Modified: `src/hivemind/eval/report.py` (full rewrite),
  `src/hivemind/policies/{dspy_compiled,dspy_train}.py` (real implementations),
  `src/hivemind/{cli,corpus/ingest}.py`,
  `pyproject.toml` (matplotlib in [dev]),
  `tests/conftest.py` (toy fixture moved),
  `docs/{evaluation/README.md,skills_corpus/sources.md,context_injection/02_dspy_compiled_skills.md}`,
  `CLAUDE.md` (routing table entry only),
  `todo/plan.md`,
  `.gitignore` (audit_log.jsonl).
