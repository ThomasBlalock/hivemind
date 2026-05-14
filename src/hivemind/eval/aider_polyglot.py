"""Inspect AI task wrapping the Aider polyglot benchmark. Scaffolded — see swe_bench_lite.py."""

from __future__ import annotations


def _require_inspect():
    try:
        import inspect_ai  # noqa: F401
    except ImportError as e:
        raise RuntimeError(
            "inspect-ai not installed. Install with: pip install -e '.[eval]'"
        ) from e


def build_task(policy: str = "baseline_a"):
    _require_inspect()
    from inspect_ai import Task, task  # type: ignore
    from inspect_ai.dataset import Sample  # type: ignore
    from inspect_ai.solver import generate, system_message  # type: ignore

    samples = [Sample(input="Placeholder Aider-polyglot task.", target="placeholder")]

    @task
    def _t() -> Task:
        from hivemind.eval.policy_adapter import inspect_solver_for_policy

        return Task(
            dataset=samples,
            solver=[system_message("HiveMind eval task."), inspect_solver_for_policy(policy), generate()],
        )

    return _t()
