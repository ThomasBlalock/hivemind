"""Minimal end-to-end fake harness. Stands in for OpenHands/Hermes in tests.

Drives a fake "agent" through one or more turns, calling the injection
adapter on each turn and recording what got spliced in. Lets us prove the
adapter contract end-to-end without vendoring a real harness.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from hivemind.harness.adapter import InProcessAdapter
from hivemind.policies.base import Chunk, Message


@dataclass
class FakeTrajectory:
    messages: list[Message] = field(default_factory=list)
    injected_chunks_per_turn: list[list[Chunk]] = field(default_factory=list)


class FakeHarness:
    """Run a deterministic fake agent. The 'agent' just echoes user input;
    the value is in proving that injection happens at the right place."""

    def __init__(self, adapter: InProcessAdapter | None = None, *, model: str = "fake-model"):
        self._adapter = adapter or InProcessAdapter()
        self._model = model

    def run(
        self,
        user_inputs: list[str],
        *,
        budget_tokens: int = 4000,
        trajectory_id: str | None = None,
    ) -> FakeTrajectory:
        traj = FakeTrajectory()
        for turn, ui in enumerate(user_inputs):
            traj.messages.append(Message(role="user", content=ui))
            resp = self._adapter.inject(
                traj.messages,
                model=self._model,
                budget_tokens=budget_tokens,
                harness="fake",
                trajectory_id=trajectory_id,
                turn_index=turn,
            )
            traj.injected_chunks_per_turn.append(resp.chunks)
            # The "agent" produces a trivial reply.
            traj.messages.append(Message(role="assistant", content=f"ack: {ui}"))
        return traj
