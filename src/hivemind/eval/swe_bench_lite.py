"""Inspect AI task wrapping SWE-bench Lite.

Scaffolded. The real SWE-bench harness needs Docker and large container
images; we don't pay that cost in unit tests. ``build_task()`` returns the
Inspect task object when ``inspect-ai`` is installed; otherwise it raises a
clear error pointing to the optional install group.

Run (when the .[eval] extra is installed):
    inspect eval -m src/hivemind/eval/swe_bench_lite.py \\
      --model anthropic/claude-sonnet-4-6 -T policy=baseline_b
"""

from __future__ import annotations


def _require_inspect():
    try:
        import inspect_ai  # noqa: F401
    except ImportError as e:
        raise RuntimeError(
            "inspect-ai not installed. Install with: pip install -e '.[eval]'"
        ) from e


def build_task(policy: str = "baseline_a", split: str = "dev"):
    """Construct the SWE-bench-Lite Inspect task with the named injection policy."""
    _require_inspect()
    from inspect_ai import Task, task  # type: ignore
    from inspect_ai.dataset import Sample  # type: ignore
    from inspect_ai.solver import generate, system_message  # type: ignore

    # TODO(plan Phase 1): wire to the actual SWE-bench Lite dataset and grader.
    # For now, return a single placeholder Sample so the runner has *something*
    # to chew on for plumbing tests.
    samples = [
        Sample(input="Placeholder SWE-bench-Lite task.", target="placeholder"),
    ]

    @task
    def _t() -> Task:
        from hivemind.eval.policy_adapter import inspect_solver_for_policy

        return Task(
            dataset=samples,
            solver=[system_message("HiveMind eval task."), inspect_solver_for_policy(policy), generate()],
        )

    return _t()
