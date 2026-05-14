"""Inspect AI solver that injects context from a named HiveMind policy.

Skipped at import time if inspect-ai isn't installed — the function only runs
inside ``build_task`` paths that already required inspect-ai.
"""

from __future__ import annotations


def inspect_solver_for_policy(policy_name: str):
    from inspect_ai.solver import Solver, solver  # type: ignore

    from hivemind.api import hub
    from hivemind.policies.base import Message, SynthesizeRequest

    @solver
    def hivemind_injection() -> Solver:
        p = hub.get_or_create(policy_name)

        async def solve(state, generate):  # noqa: ANN001
            # state.user_prompt.text is the current user content in Inspect AI.
            conv = [Message(role="user", content=state.user_prompt.text)]
            req = SynthesizeRequest(
                conversation=conv,
                model=state.model.name if hasattr(state, "model") else "unknown",
                budget_tokens=4000,
                harness="inspect_ai",
            )
            resp = p.synthesize(req)
            for c in resp.chunks:
                # Append to system message (the canonical "system_suffix" position).
                state.messages.insert(0, {"role": "system", "content": c.content})
            return state

        return solve

    return hivemind_injection()
