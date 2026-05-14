# System 3 — Trajectory-Conditioned Online Bandit

**Status:** designed. Depends on System 2 as warm start, and on real harness integrations producing `/feedback` traffic. Tracked in [../../todo/plan.md](../../todo/plan.md) Phase 5.

This is the system that closes the feedback loop CLAUDE.md called out as the differentiator. It's the one that justifies the "class of models in agent harnesses for context injection" framing.

## Core idea

Treat context injection as a **contextual bandit**. The state describes where the agent is *right now in this trajectory*; the action is the set of skills (and their distillation levels and positions) to inject; the reward is downstream task success per token spent. Policy updates from both offline eval (like System 2) and online feedback (new).

## State

- Embedding of the last 3 turns (voyage-3, mean-pooled)
- Model id (one-hot)
- Harness id (one-hot)
- Turn index (the call may be mid-trajectory, not just turn 1)
- Hash of skills already injected earlier this trajectory
- Names of in-flight tool calls (small fixed-vocab embedding)
- Optional client-supplied progress signal (e.g. tests passing / failing count)

## Action

- A *set* of skills. Combinatorial → approximated by per-skill independent inclusion bandits, then greedy-packed under `budget_tokens`.
- Distillation level per included skill ∈ {full, medium, minimal} — sources the three variants from System 2's compiled artifacts.
- Position per skill (mostly `system_suffix`; bandit may also choose `pre_tools` for tool-related skills).

## Reward

- Success rate × (1 − α · cost_norm), α configurable.
- **Offline:** computed by the eval harness like System 2.
- **Online:** posted by harnesses to `POST /feedback` per [the API](../agent_harness/integration.md). Opt-in; reward and hashed state only, no raw conversation.

## Algorithm

- Per-skill **LinUCB** or **Thompson sampling** over the state featurization.
- Warm start by importing System 2's frozen decisions as off-policy expert demonstrations.
- Stage 2 (when ~100k feedback samples accumulate): a small joint MLP policy on top, trained off-policy.

## Mid-trajectory injection

System 3 is the first that uses the `turn_index` field meaningfully. A harness can call `/synthesize` every turn, not just at session start:

- Turn 1: cold state, behaves like System 2.
- Turn N>1: state includes "what's already been tried, what's failing"; policy may inject a recovery skill (debugger workflow, error-pattern reference, etc.).

This requires the harness to actually issue per-turn calls — added in the [agent harness integration](../agent_harness/README.md) once System 1 ships.

## Privacy

- Feedback is opt-in per-client and per-trajectory.
- Clients send: trajectory_id, hashed state vector, scalar reward, cost, turn count.
- **Never** the raw conversation. This is enforced server-side by rejecting unhashed payloads on `POST /feedback`.
- An offline-only frozen snapshot of the policy is published per release, so anyone can reproduce eval numbers without trusting our online updates.

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| No traffic → no online benefit | Architecture works fine as System 2 in the meantime. Document degraded-mode behavior. |
| Bandit policies are hard to debug | Every action logged with score breakdown; offline replay tool ships with the policy. |
| Reward hacking by clients | Reward is bounded; outlier detection on the per-client reward distribution; ban clients who exceed sanity thresholds. |
| Distribution shift between offline eval and production | Periodic offline re-validation; alert if held-out eval-suite perf regresses past a threshold. |

## Why this is the most promising

- Closes the loop. CLAUDE.md's "bonus points if the system uses the results of the workflow to train itself" — this is that.
- Network effects: more integrations → more feedback → better policy → more integrations want in.
- Mid-trajectory injection unlocks a behavior category neither System 1 nor System 2 can match (in-flight recovery from agent failure modes).

## Implementation

- File: `src/policies/online_bandit.py`
- Online state in `data/bandit/<policy_version>/` (versioned; periodic snapshots committed for reproducibility)
- Inherits System 1's retrieval frontend and System 2's distilled bodies; replaces the selection/ordering tail with the bandit policy
- Same [API](../agent_harness/integration.md); response carries `policy: "online_bandit@v1"`

## Dependencies

- `numpy`, `scikit-learn` (LinUCB/Thompson primitives)
- All of System 1's and System 2's dependencies
- Storage: sqlite per-snapshot; postgres if we outgrow it (don't optimize early)
