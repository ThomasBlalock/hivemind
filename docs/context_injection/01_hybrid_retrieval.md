# System 1 — Hybrid Retrieval with Reranking

**Status:** designed. Implementation tracked in [../../todo/plan.md](../../todo/plan.md) Phase 5.

The minimum-viable upgrade from keyword triggers. All components are off-the-shelf — no training, no online state, no model-specific behavior. The goal is a credible, well-instrumented baseline that the next systems must beat.

## What problem this fixes

Baseline B (naive keyword) has known failure modes; this system targets the easy ones:

| Failure mode | Example | Fixed here? |
|---|---|---|
| Paraphrase / synonym miss | "debug a flaky CI run" doesn't match `test` trigger | yes — dense retrieval |
| Multi-turn relevance | keyword appeared in turn 1, mattered at turn 5 | partial — we look at last 3 turns |
| Unbounded injection | 10 triggers fire → 10 skills dumped | yes — token-budget packing |
| Naive false positives | "don't use rebase" still fires rebase skill | partial — reranker handles many but not all negations |

The unfixed failure modes (skills still verbose, no per-model tailoring, no learning from outcomes) are what motivate [System 2](02_dspy_compiled_skills.md) and [System 3](03_online_bandit.md).

## Pipeline

```
conversation ── query construction ──┐
                                     ├─► dense retrieval (voyage-3, LanceDB)  ─┐
                                     │                                          ├─► RRF ─► top-20
                                     └─► sparse retrieval (bm25s)              ─┘            │
                                                                                              ▼
                                                                                  cross-encoder rerank
                                                                                              │
                                                                                              ▼
                                                                                drop score < τ
                                                                                              │
                                                                                              ▼
                                                                                  greedy pack under budget
                                                                                              │
                                                                                              ▼
                                                                              chunks [{content, system_suffix, ...}]
```

## Design decisions

### Query construction
- Last user message + previous 2 turns concatenated, role tags stripped.
- Plus any in-flight tool-call names from the most recent assistant turn.
- **Why not just the last message:** misses context after the agent has done work; the "moment of relevance" is often after the trigger word.
- **Why not the full conversation:** dilutes the embedding; voyage-3 truncates anyway and the noise hurts more than the early-context signal helps.
- **Why no LLM-extracted "intent":** adds 200–500 ms; revisit if precision is the bottleneck after ablation.

### Indexes
- **Dense:** `voyage-3` over `title + description + body[:200_tokens]`. Storing only the first 200 tokens of body keeps the embedding focused — full bodies dilute the vector.
- **Sparse:** `bm25s` (fast, in-process) over `title + description + triggers + body`. Original keyword triggers from baseline B are still tokens in the bag — turns them into a co-signal instead of throwing them away.
- Both rebuild on every corpus version. LanceDB lets us version vectors alongside the corpus.

### Retrieval
- `K_dense = 40`, `K_sparse = 40`.
- Reciprocal Rank Fusion (RRF) merge → `K_candidates = 20`.
- Cross-encoder rerank with `voyage rerank-2` (fallback: `cohere rerank-3`). Reranking 20 items is cheap (~60 ms).
- Drop candidates with rerank score < τ (start τ = 0.3; calibrate after Phase 4 baselines run).

### Budget packing
- Greedy: sort by rerank score descending, add until adding the next skill would exceed `budget_tokens`.
- Reserve 10% headroom on the declared budget for safety against tokenizer drift.
- Skills are **atomic** in v1 — never truncate a body mid-skill (System 2 handles compression properly).

### Injection
- All selected chunks: `position: system_suffix`. Simplest, same place skills already live in harnesses.
- Order: highest rerank score first → most-relevant skill nearest the system prompt, where attention is strongest.

### Caching
- LRU cache on `hash(query) → reranked top-N skill_ids`, TTL 5 min, size 10k.
- Within a single trajectory, similar queries recur (multi-turn → small query delta) and caching pays off.

## Latency budget

| Step | Approx ms |
|---|---|
| Query embed (voyage-3) | 30 |
| Dense ANN (LanceDB) | 5 |
| BM25 search (bm25s) | 10 |
| RRF merge | <1 |
| Rerank top-20 | 60 |
| Pack + serialize | 5 |
| **Total** | **~110 ms** |

Within the 200 ms p50 target ([../serving/README.md](../serving/README.md)). Allows headroom for cold-cache spikes.

## Implementation

- File: `src/policies/hybrid_retrieval.py`
- Classes: `HybridIndexer` (build-time), `HybridRetrievalPolicy` (serve-time)
- `HybridRetrievalPolicy.synthesize(req) -> resp` matches [the API contract](../agent_harness/integration.md)
- Dependencies (pinned): `voyageai`, `cohere` (fallback), `lancedb`, `bm25s`
- Corpus input: `src/corpus/skills.jsonl` per [ingestion.md](../skills_corpus/ingestion.md)

## Ablations for Phase 6

- Dense only / BM25 only / hybrid no rerank / full pipeline
- Query window size: last 1, 3, 5 turns
- `τ` sweep: 0.0, 0.2, 0.3, 0.5
- Budget sweep: 1k, 2k, 4k tokens

These quantify which components carry the weight and inform System 2's optimizer search space.

## What this can't do (and which system fixes it)

| Limitation | Fixed by |
|---|---|
| Skills still verbose; tokens wasted on prose | [System 2](02_dspy_compiled_skills.md) |
| Same chunks for every model | [System 2](02_dspy_compiled_skills.md) |
| Threshold and budget choices hand-tuned | [System 2](02_dspy_compiled_skills.md) |
| One synthesis call per trajectory; no mid-trajectory recovery | [System 3](03_online_bandit.md) |
| No learning from outcomes | [System 3](03_online_bandit.md) |
