"""System 3 — Trajectory-Conditioned Online Bandit.

Design: docs/context_injection/03_online_bandit.md

Implements per-skill independent LinUCB over a small state featurization,
warm-started from System 2's frozen decisions. Online updates come from
``POST /feedback``.

Ships **scaffolded**: with no observed feedback, this policy is mathematically
indistinguishable from System 2 (uniform priors → same packing). It becomes
meaningful as feedback accumulates.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

import numpy as np

from hivemind.config import default_corpus_path, models_dir
from hivemind.corpus.ingest import load_jsonl
from hivemind.corpus.schema import Skill
from hivemind.policies.base import Chunk, Message, SynthesizeRequest, SynthesizeResponse
from hivemind.policies.dspy_compiled import DSPyCompiledPolicy

FEATURE_DIM = 32  # state featurization size; modest, easy to learn

UCB_ALPHA = 1.0  # exploration coefficient


def _featurize(req: SynthesizeRequest) -> np.ndarray:
    """Hash conversation + model + turn index into a fixed-size feature vector.

    The real System 3 would use a learned conv embedding; this hash-based
    featurization keeps the bandit math runnable without external services.
    """
    vec = np.zeros(FEATURE_DIM, dtype=np.float32)
    last = req.conversation[-1].content if req.conversation else ""
    for tok in last.lower().split():
        vec[int(hashlib.md5(tok.encode()).hexdigest(), 16) % FEATURE_DIM] += 1.0
    # Append model + turn signals into stable buckets.
    vec[int(hashlib.md5(req.model.encode()).hexdigest(), 16) % FEATURE_DIM] += 1.0
    if req.turn_index is not None:
        vec[FEATURE_DIM - 1] = min(req.turn_index, 10) / 10.0
    n = np.linalg.norm(vec)
    return vec / n if n > 0 else vec


class _LinUCBArm:
    """One arm per skill. Maintains A, b for closed-form LinUCB.

    See Li et al. 2010, "A Contextual-Bandit Approach to Personalized News
    Article Recommendation".
    """

    def __init__(self, d: int):
        self.A = np.eye(d, dtype=np.float64)
        self.b = np.zeros(d, dtype=np.float64)
        self.updates = 0

    def score(self, x: np.ndarray, alpha: float) -> float:
        A_inv = np.linalg.inv(self.A)
        theta = A_inv @ self.b
        mean = float(theta @ x)
        bonus = alpha * float(np.sqrt(x @ A_inv @ x))
        return mean + bonus

    def update(self, x: np.ndarray, reward: float) -> None:
        x = x.astype(np.float64)
        self.A += np.outer(x, x)
        self.b += reward * x
        self.updates += 1


class OnlineBanditPolicy:
    name = "online_bandit@v1"

    def __init__(self, skills: list[Skill], state_dir: Path | None = None):
        self._skills = skills
        self._skills_by_id = {s.id: s for s in skills}
        self._base = DSPyCompiledPolicy(skills)
        self._arms: dict[str, _LinUCBArm] = {s.id: _LinUCBArm(FEATURE_DIM) for s in skills}
        self._pending: dict[str, list[tuple[str, np.ndarray]]] = {}  # trajectory_id -> [(skill_id, x)]
        self._state_dir = state_dir or (models_dir() / "bandit" / "v1")
        self._load_state()

    # --- persistence ----------------------------------------------------

    def _load_state(self) -> None:
        p = self._state_dir / "arms.npz"
        if not p.exists():
            return
        data = np.load(p, allow_pickle=False)
        for s in self._skills:
            key_a = f"A__{s.id}"
            key_b = f"b__{s.id}"
            if key_a in data and key_b in data:
                self._arms[s.id].A = data[key_a]
                self._arms[s.id].b = data[key_b]

    def save_state(self) -> Path:
        self._state_dir.mkdir(parents=True, exist_ok=True)
        kv: dict[str, np.ndarray] = {}
        for sid, arm in self._arms.items():
            kv[f"A__{sid}"] = arm.A
            kv[f"b__{sid}"] = arm.b
        p = self._state_dir / "arms.npz"
        np.savez(p, **kv)
        return p

    # --- core ------------------------------------------------------------

    def synthesize(self, req: SynthesizeRequest) -> SynthesizeResponse:
        t0 = time.perf_counter()
        # Use System 2 to produce a candidate set + ordered chunks; we override
        # selection with the bandit's UCB scores. Until any feedback arrives,
        # all arms have identical priors and we follow System 2 exactly.
        base = self._base.synthesize(req)
        if not base.chunks:
            return SynthesizeResponse(chunks=[], policy=self.name, tokens=0, latency_ms=0)

        x = _featurize(req)
        ucb_scored: list[tuple[Chunk, float]] = []
        for c in base.chunks:
            arm = self._arms.get(c.skill_id)
            if arm is None:
                continue
            ucb_scored.append((c, arm.score(x, UCB_ALPHA)))
        ucb_scored.sort(key=lambda cs: -cs[1])

        # Pack under the original budget using existing chunk tokens.
        from hivemind.tokenize import count_tokens
        chunks: list[Chunk] = []
        total_tokens = 0
        budget = int(req.budget_tokens * 0.9)
        for c, score in ucb_scored:
            t = count_tokens(c.content)
            if total_tokens + t > budget:
                continue
            chunks.append(Chunk(**{**c.model_dump(), "score": score}))
            total_tokens += t

        # Record what we played for this trajectory so feedback can update arms.
        if req.trajectory_id is not None:
            self._pending.setdefault(req.trajectory_id, [])
            for c in chunks:
                self._pending[req.trajectory_id].append((c.skill_id, x))

        latency_ms = int((time.perf_counter() - t0) * 1000)
        return SynthesizeResponse(
            chunks=chunks, policy=self.name, tokens=total_tokens, latency_ms=latency_ms
        )

    # --- feedback --------------------------------------------------------

    def record_feedback(self, trajectory_id: str, success: bool, cost_usd: float) -> int:
        """Apply a reward to every arm pulled during the trajectory. Returns # arms updated.

        Reward = success - alpha * cost_norm. cost_norm = cost_usd capped at 1.0.
        """
        if trajectory_id not in self._pending:
            return 0
        reward = (1.0 if success else 0.0) - 0.5 * min(cost_usd, 1.0)
        n = 0
        for skill_id, x in self._pending.pop(trajectory_id):
            arm = self._arms.get(skill_id)
            if arm is None:
                continue
            arm.update(x, reward)
            n += 1
        return n


def _factory():
    skills = load_jsonl(default_corpus_path())
    skills = [s for s in skills if s.audit_status == "passed"]
    return OnlineBanditPolicy(skills)


def __register():
    from hivemind.policies.registry import register_policy
    register_policy("online_bandit", _factory)


__register()
