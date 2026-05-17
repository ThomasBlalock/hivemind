# Autonomous Session Plan

For a fresh Claude Code session to execute. The user is away; goal is to land the four items below in order while burning Claude Code credit (not external API credit). **Stop by ~1pm local time.**

---

## Session prep (read this first)

### Repo state right now (commit `6340ef0`)
- HiveMind core service is built and tested: corpus pipeline, 5 policies (baselines + Systems 1/2/3), FastAPI service, adapter layer.
- mini-swe-agent integration shipped (`src/hivemind/harness/mini_swe_runner.py`) with static + dynamic injection modes, sweep script, 2 toy eval tasks.
- **31 tests pass, 2 skip** (live-backend skipifs). `ruff check src tests scripts` is clean.
- Toy corpus has **3 skills** under `corpus/skills/`.
- `corpus/skills.jsonl` built and current.

### Critical context

- **No API keys are set.** `VOYAGE_API_KEY`, `OPENROUTER_API_KEY`, `ANTHROPIC_API_KEY` are all unset. Embedder/reranker fall back to deterministic stubs. **Do not** call out to paid services in this session.
- **Don't push to a remote.** No remote is configured for these commits anyway, but don't try to add one.
- **Commit incrementally on `main`** after each option below completes. Use HEREDOC commit messages and the `Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>` footer (see prior commits with `git log --oneline -5`).
- The user has already heavily customized [`README.md`](../README.md). **Do not revert** any prose there.

### How to work

```bash
source .venv/bin/activate
# always activate before pytest / ruff / scripts
```

- Tests: `pytest`
- Lint: `ruff check src tests scripts` (and `--fix` for auto-fixes)
- Existing test fixtures: `tests/conftest.py` provides `toy_corpus_dir`, `toy_skills`, `built_corpus`, `isolated_corpus`
- Run the existing sweep with stubs: `python scripts/run_harness_sweep.py --dry-run` (zero cost)
- Run the demo: `python scripts/compare_policies.py`

### Conventions to respect

- All new code lives under `src/hivemind/`; tests under `tests/`; scripts under `scripts/`.
- Pydantic v2 for schemas (`from pydantic import BaseModel`).
- Type hints with `from __future__ import annotations`.
- Each policy module registers itself via a private `__register()` at import time.
- External backends are abstracted behind `Protocol` classes with a stub default and a real backend gated on env var (see `src/hivemind/embeddings.py`, `src/hivemind/reranker.py`).
- Optional deps go in `pyproject.toml` extras (`live`, `eval`, `dspy`, `dev`). New heavy deps probably want their own extra.
- Read `docs/` before editing anything substantial. `CLAUDE.md` has the routing table.

### What `/synthesize` returns

`Chunk` has `content`, `position`, `skill_id`, `source_sha`, `score`. `SynthesizeResponse` has `chunks`, `policy`, `tokens`, `latency_ms`. Read `src/hivemind/policies/base.py` for the canonical types.

### If something blocks you

- **Network unreachable** → stop, document, move to the next option. Don't loop.
- **External lib import failure** → make it an optional extra; add an import guard with a clear "install with pip install -e '.[<extra>]'" message.
- **Tests start failing on unrelated code** → revert your last change to that file; investigate; do not bypass.
- **An option turns out to be 3x bigger than expected** → ship a smaller version that's a clear "step 1 of N", commit it, move on. Update this plan with what's left.

---

## Option 4 — Results dashboard + reporting (FIRST)

**Why first:** smallest, well-scoped, fully testable offline. Producing the perf-vs-cost chart is the project's stated end-state (CLAUDE.md), so even a scaffolded version compounds value the moment the user runs a real sweep.

### What to build

1. **Replace** `src/hivemind/eval/report.py`. Current contents are an Inspect-AI-flavored stub that doesn't match our sweep CSV schema. The sweep writes rows with these fields (see `scripts/run_harness_sweep.py`):
   ```
   run_idx, task_id, model_arg, model, policy, success, exit_status,
   cost_usd, n_calls, n_chunks, chunk_ids (comma-joined), error, submission
   ```

2. **Public API in `src/hivemind/eval/report.py`:**
   - `load_sweep_csv(path) -> list[dict]` — parse a sweep CSV; coerce types (success → bool, cost_usd → float, etc.); split `chunk_ids` back to a list.
   - `aggregate(rows) -> dict` — return a dict with:
     - `by_cell`: list of one record per (model × policy), with `n_runs`, `n_tasks`, `success_rate`, `mean_cost`, `total_cost`, `mean_n_chunks`.
     - `by_skill`: dict `skill_id -> {n_fires, by_task, by_policy}` from the joined `chunk_ids` column.
     - `pairwise`: for each (model, policy ≠ baseline_a), the success-rate delta vs. baseline_a on the same model+task set; include a basic bootstrap CI (1000 resamples).
   - `markdown_report(agg, *, title=None) -> str` — human-readable markdown with sections: Headline, Per-cell table, Skill coverage, Pairwise deltas.
   - `perf_vs_cost_chart(agg, out_png)` — matplotlib scatter, one point per (model, policy), x = mean cost per task, y = success rate, color = model, marker = policy. Add labels. Save PNG.

3. **CLI:** `scripts/build_report.py`
   ```
   python scripts/build_report.py <sweep_csv> [--out-md report.md] [--out-png perf_vs_cost.png]
   ```
   Defaults: write to the same directory as the input CSV.

4. **Synthetic data:** add a `scripts/synthesize_sweep_csv.py` that emits a fake but plausible sweep CSV (50–100 rows across 3 models × 3 policies × 4 tasks × 3 runs) so the reporting pipeline can be smoke-tested without a real sweep. Use a deterministic seed. The fake data should reflect the *expected* shape of results (hybrid_retrieval slightly above baselines on tasks where a matching skill exists; flat elsewhere) so the chart looks meaningful.

5. **Dependencies:**
   - Add `matplotlib>=3.8` to the `dev` extra (cheap, no external services).
   - Do **not** add scipy; bootstrap is fine with pure numpy.

6. **Tests** (`tests/test_report.py`):
   - `load_sweep_csv` round-trips a written CSV.
   - `aggregate` produces a sensible summary for a small hand-crafted input.
   - `markdown_report` returns non-empty markdown with all expected sections.
   - `perf_vs_cost_chart` writes a PNG > 0 bytes (don't assert image contents).
   - Run the synthesize-sweep script → build_report → assert no errors and outputs exist.

7. **Docs:**
   - Add `docs/evaluation/reporting.md` (link from `docs/evaluation/README.md` and update the CLAUDE.md docs table).
   - Document the synthetic-data path so the user can preview the report shape immediately.

### Acceptance for Option 4

- `pytest` passes (33+ tests).
- `ruff check` clean.
- Running `python scripts/synthesize_sweep_csv.py --out /tmp/fake.csv && python scripts/build_report.py /tmp/fake.csv --out-md /tmp/r.md --out-png /tmp/r.png` succeeds and produces both files non-empty.
- One commit: title "Add results dashboard: aggregation, markdown report, perf-vs-cost chart" with a clear body.

---

## Option 3 — Real DSPy programs for System 2 (SECOND)

**Why second:** structural; doesn't need internet beyond `pip install`. Turns the current stub (loads artifacts if present) into a real (untrained) compiler.

### What to build

1. **Module: `src/hivemind/policies/dspy_programs.py`** (new file, separate from `dspy_compiled.py` which is the serve-time policy). Define three DSPy modules:
   - `SkillDistiller(dspy.Module)` — `forward(raw_body, target_model) -> distilled_body`. Uses `dspy.ChainOfThought` with a signature like `"raw_skill, target_model -> distilled_skill"` plus an instruction string explaining "preserve all actionable instructions, drop human-only prose, keep under N tokens."
   - `SkillSelector(dspy.Module)` — `forward(query, skill_candidate, target_model) -> include: bool, confidence: float`. Signature with a clear rubric in the instruction.
   - `SkillOrderer(dspy.Module)` — `forward(selected_skill_ids, query, target_model) -> permutation: list[int]`. Signature returns indices.

2. **Trainer: rewrite `src/hivemind/policies/dspy_train.py`** with a real `main()`:
   - Loads audited corpus.
   - Configures `dspy.LM` from env (`HIVEMIND_DSPY_LM`, fall back to a `dspy.DummyLM` if `HIVEMIND_DSPY_DRY_RUN=1` — important for tests).
   - Trains using `dspy.MIPROv2` (or `dspy.BootstrapFewShot` if MIPRO isn't available in the installed version — check `dspy.__version__` and branch).
   - Reward signal abstracts as `def reward_fn(example, prediction) -> float`. For now this is a tiny synthetic reward (e.g., reward = 1 if `distilled_body` is shorter than raw and contains "command:" or "step" keywords; for selector, reward = 1 if `include` matches a hand-labeled mini set) so that training has signal without an LLM evaluator. Document clearly that the real reward comes from the eval harness and slots in later.
   - Hard cap on training cost: a `--max-lm-calls` arg; abort if exceeded.
   - Saves artifacts to `models/dspy/v<ver>/` matching what `dspy_compiled.py` already loads:
     - `distillations.jsonl` (one row per `{skill_id, model, body}`)
     - `selector.json` (`{skill_id: {model: {logit: float}}}`)
     - `order_prior.json` (`{skill_id: {model: float}}` — position prior)

3. **CLI:** `hivemind dspy train [--out-version v1] [--max-lm-calls 100] [--dry-run]` — add to `src/hivemind/cli.py`.

4. **Update `src/hivemind/policies/dspy_compiled.py`:**
   - Currently loads only `distillations.jsonl`. Extend `_load_artifacts` to also load `selector.json` and `order_prior.json`.
   - Apply the selector to filter chunks before packing.
   - Apply the order prior to break ties in System 1's rerank score.
   - Keep the System-1-degraded fallback intact when artifacts are empty.

5. **Dependencies:**
   - Already declared in the `dspy` extra in `pyproject.toml`. Don't move it to the base install — keep it optional.
   - The `dspy_compiled` policy must continue to work when `dspy-ai` is NOT installed (it doesn't import dspy itself; only `dspy_programs.py` and `dspy_train.py` do).

6. **Tests** (`tests/test_dspy_programs.py`):
   - Gate the test module on `pytest.importorskip("dspy")`.
   - Use `dspy.DummyLM` (returns canned responses) so no network call happens.
   - Exercise each program once.
   - Run the trainer with `--dry-run` and assert that artifact files appear on disk.
   - Round-trip: train (with DummyLM) → load via `DSPyCompiledPolicy` → confirm the policy serves chunks.

7. **Docs:**
   - Update `docs/context_injection/02_dspy_compiled_skills.md`: the "Implementation" section now points at concrete files; note the synthetic-reward stand-in and what needs to swap in.
   - Add a note under "Risks" about the synthetic reward distorting training signal.

### Acceptance for Option 3

- `pip install -e '.[dspy,dev]'` works.
- `pytest` passes (some new tests skip if dspy not present).
- `pytest tests/test_dspy_programs.py` passes with dspy installed.
- `hivemind dspy train --dry-run` produces the three artifact files.
- After training (dry-run), `hivemind` server with `--policy dspy_compiled` serves chunks for a relevant query.
- One commit.

---

## Option 1 — Real skills corpus (THIRD)

**Why third:** biggest scope; benefits most from the strengthened reporting and DSPy training already in place. Done third, the user wakes up to a corpus they can immediately measure with.

### What to build

1. **Source adapters under `src/hivemind/corpus/sources/`** (new package). Each adapter knows how to fetch + normalize one source into our `Skill` schema. Start with **two** sources to keep blast radius small:
   - `anthropic_skills.py` — pull from the `anthropics/skills` GitHub repo at a pinned commit. Use the `gh` CLI via subprocess (`gh api repos/anthropics/skills/contents/<path>`) — `gh` is already on the box and avoids unauthenticated rate limits.
   - `openhands_microagents.py` — pull from `All-Hands-AI/OpenHands` at a pinned commit, path `microagents/` (verify the path).

2. **Skill normalization:** each source adapter returns a list of `Skill` instances. Token-count via the existing `count_tokens`. Source string is `<repo>@<commit-sha>` (record the commit you pinned).

3. **CLI:** `hivemind corpus pull [--sources anthropic_skills openhands_microagents] [--out corpus/skills/]`
   - Writes one markdown file per skill under `corpus/skills/<source>__<skill_id>.md` in our frontmatter format.
   - Then user can run the existing `hivemind corpus build` to ingest.

4. **Security audit log:** when ingestion runs and a skill hits `manual_review_required` or `failed`, append a row to `corpus/audit_log.jsonl` with `skill_id`, `source`, `status`, `notes`, `timestamp`. Update `src/hivemind/corpus/ingest.py` to write this log.

5. **Target size:** **don't try for 500.** Aim for 30–80 skills total across the two sources. If a source has hundreds, sample down. Bigger isn't the point — clean, audited, working is the point.

6. **Tests** (`tests/test_corpus_sources.py`):
   - **Mock network calls** with `pytest.MonkeyPatch` replacing the `gh` subprocess call with a small in-process fixture (write a fake gh response under `tests/fixtures/gh_*.json`). This is a test-isolation hard rule; do NOT make these tests hit GitHub.
   - Verify each adapter produces well-formed Skill objects with non-empty bodies and reasonable token counts.

7. **Docs:**
   - Update `docs/skills_corpus/sources.md` with the concrete adapters that exist and which commit shas they pin.
   - Add an `corpus/audit_log.jsonl` line in `.gitignore` so it doesn't get committed by accident (the audit log is per-environment).
   - Add a `corpus/PROVENANCE.md` listing source repos + pinned shas + skill counts.

### Caveats specific to this option

- The `gh` CLI may or may not be authenticated for this machine. If not, fall back to plain `curl` or `urllib` against the github API (unauthenticated rate limits = 60/hr, fine for our scale). Probe `gh auth status` first.
- Anthropic Skills follow a specific frontmatter format; OpenHands microagents follow a different one. Adapters must reconcile both into our schema. See `docs/skills_corpus/ingestion.md`.
- **Do not pull files that fail the security audit** into the served corpus. Run audit at ingestion time and skip hard-fails.

### Acceptance for Option 1

- `hivemind corpus pull --sources anthropic_skills` produces N>10 markdown files under `corpus/skills/`.
- `hivemind corpus build` ingests them; jsonl has audit_status counts logged.
- Existing tests still pass (toy corpus tests use `toy_corpus_dir` fixture which is the 3-skill canon; either preserve those by keeping the 3 toy skills in place, or update the fixture to point at a snapshot dir).
- `pytest` passes.
- One commit.

---

## Option 2 — More eval tasks (LAST)

**Why last:** lowest risk, easiest to ship as a partial. The other three options unlock more value if completed; this one is "more of the same."

### What to build

- 10–15 self-contained bug-fix tasks under `eval_tasks/<id>/` matching the existing format:
  - `task.yaml` (id, prompt, test_cmd, optional setup_cmd)
  - `repo/` (the buggy code + pytest tests)
- Cover a spread of difficulties:
  - **Easy:** off-by-one, missing return, wrong operator, simple typo (5 tasks)
  - **Medium:** regex fixes, sort comparator, dict default mutability, generator vs list (5 tasks)
  - **Harder:** small refactor + correctness fix combined, signal-handling or context-manager bugs, race-y patterns made deterministic (5 tasks)
- Each task's `prompt` should be naturally phrased, NOT mention the skill names from the corpus. The retrieval system has to find them.
- Each task should have a **single failing test** as the success signal; tasks should be solvable in <10 agent turns.
- Add `eval_tasks/README.md` listing each task with a one-line summary + difficulty tier.

### Tests

- `tests/test_eval_tasks.py` walks `eval_tasks/`, loads each `task.yaml`, asserts:
  - Pydantic-validatable shape.
  - `test_cmd` exists and is non-empty.
  - The bug actually causes the test to fail (run `pytest --collect-only` in each repo dir, and run the actual test to confirm it fails — this catches "I forgot to introduce the bug" mistakes).

### Acceptance for Option 2

- ≥10 new tasks total under `eval_tasks/`.
- `pytest tests/test_eval_tasks.py` passes (each task fails its own test in its `repo/`, which is expected and asserted).
- Existing tests still pass.
- One commit.

---

## Wrap-up

At the end of the session, write a short summary into `todo/session_log_<date>.md` with:
- What shipped (which options completed in full, which partial).
- Test counts before and after.
- Any TODOs that surfaced.
- Outstanding follow-ups for the user.

Then update `todo/plan.md` to check off any newly-completed items (notably under Phases 1, 3, 5, 6).

### Do NOT do

- Don't push to a remote.
- Don't run anything that calls a paid API (Voyage, OpenRouter, Anthropic, OpenAI).
- Don't add new top-level prose to README.md without checking — user maintains it.
- Don't change `CLAUDE.md` body content; only update the docs routing table if new docs are added.
- Don't bump existing dependency pins unless something concretely breaks.

### Time/effort estimate

Rough Claude-Code effort:
- Option 4: 30–60 min
- Option 3: 60–90 min
- Option 1: 60–120 min (depends on how cooperative the source repos are)
- Option 2: 45–75 min

If you're approaching 1pm and haven't started an option, **don't start it**. Update this plan with what's left and write the session log.
