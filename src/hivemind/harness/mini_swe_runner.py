"""Run a HiveMind-injected mini-swe-agent against a single task.

mini-swe-agent (`pip install mini-swe-agent`) is a ~100-line agent from the
SWE-agent team. We chose it as the first integration target because:

- Python-native API: ``DefaultAgent(model, env).run(task)``.
- Linear messages → cleanly hookable, including mid-trajectory.
- Built-in LiteLLM + native OpenRouter model adapters.
- LiteLLM gives us cost reporting for free per call.

Design: docs/agent_harness/integration.md, todo/harness_integration_plan.md.

This module exposes two modes:

- **static injection** (default): one call to ``/synthesize`` before ``run()``
  starts; chunks land in the system prompt. Validates Systems 1 + 2.
- **dynamic injection**: a subclass of ``DefaultAgent`` that calls
  ``/synthesize`` again on each step, appending new chunks as system
  messages. Validates System 3's mid-trajectory design.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

# Side-effect imports so every policy is registered before the adapter looks it up.
import hivemind.policies.baseline  # noqa: F401, E402
import hivemind.policies.dspy_compiled  # noqa: F401, E402
import hivemind.policies.hybrid_retrieval  # noqa: F401, E402
import hivemind.policies.online_bandit  # noqa: F401, E402
from hivemind.harness.adapter import InProcessAdapter
from hivemind.policies.base import Chunk, Message, SynthesizeRequest

# --- config loading --------------------------------------------------------

def _load_default_agent_config() -> dict[str, Any]:
    """Load mini-swe-agent's bundled default.yaml as a dict."""
    import minisweagent

    cfg_path = Path(minisweagent.__file__).parent / "config" / "default.yaml"
    return yaml.safe_load(cfg_path.read_text())


# Sentinel appended to the system_template so injected chunks appear at the
# end of the system prompt — equivalent to our "system_suffix" position.
_HIVEMIND_BLOCK = """

{%- if hivemind_skills %}
<hivemind_skills>
The following skills are relevant to the task. Apply them when applicable.

{{ hivemind_skills }}
</hivemind_skills>
{%- endif %}
"""


def _augmented_system_template(base_template: str) -> str:
    return base_template.rstrip() + _HIVEMIND_BLOCK


def _format_chunks(chunks: list[Chunk]) -> str:
    if not chunks:
        return ""
    parts = []
    for c in chunks:
        parts.append(f"### Skill: {c.skill_id}\n\n{c.content.strip()}")
    return "\n\n---\n\n".join(parts)


# --- result type -----------------------------------------------------------

@dataclass
class HarnessResult:
    task_id: str
    policy: str
    model: str
    success: bool
    exit_status: str
    cost_usd: float
    n_calls: int
    n_chunks: int
    chunk_ids: list[str] = field(default_factory=list)
    error: str | None = None
    submission: str = ""
    extra: dict[str, Any] = field(default_factory=dict)


# --- runner ----------------------------------------------------------------

@dataclass
class TaskSpec:
    id: str
    prompt: str
    work_dir: Path
    test_cmd: str | None = None
    setup_cmd: str | None = None


def run_task(
    task: TaskSpec,
    *,
    model: Any,
    policy_name: str,
    budget_tokens: int = 4000,
    step_limit: int = 30,
    cost_limit_usd: float = 1.0,
    dynamic: bool = False,
) -> HarnessResult:
    """Run one task with HiveMind injection. ``model`` is any mini-swe-agent
    Model subclass (LitellmModel, OpenRouterModel, DeterministicModel, ...)."""
    from minisweagent.agents.default import DefaultAgent
    from minisweagent.environments.local import LocalEnvironment

    # 1) HiveMind synthesizes context once up front.
    adapter = InProcessAdapter(policy_name=policy_name)
    req = SynthesizeRequest(
        conversation=[Message(role="user", content=task.prompt)],
        model=str(getattr(getattr(model, "config", None), "model_name", "unknown")),
        budget_tokens=budget_tokens,
        harness="mini-swe-agent",
        trajectory_id=task.id,
        turn_index=0,
    )
    synth = adapter.inject(
        conversation=req.conversation,
        model=req.model,
        budget_tokens=req.budget_tokens,
        harness=req.harness,
        trajectory_id=req.trajectory_id,
        turn_index=req.turn_index,
    )
    chunks_text = _format_chunks(synth.chunks)

    # 2) Build a config with our augmented system_template.
    base = _load_default_agent_config()
    agent_kwargs = dict(base["agent"])
    agent_kwargs["system_template"] = _augmented_system_template(agent_kwargs["system_template"])
    agent_kwargs["step_limit"] = step_limit
    agent_kwargs["cost_limit"] = cost_limit_usd

    # 3) Local env, but with cwd pinned to the task directory.
    env_kwargs = dict(base.get("environment", {}))
    env_kwargs.setdefault("env", {})
    env_kwargs.setdefault("cwd", str(task.work_dir))
    env = LocalEnvironment(**env_kwargs)

    # 4) Wire up the agent.
    AgentClass = _DynamicReinjectionAgent if dynamic else DefaultAgent
    if dynamic:
        agent = AgentClass(model=model, env=env, _hivemind_adapter=adapter, _hivemind_task=task,
                           _hivemind_budget=budget_tokens, **agent_kwargs)
    else:
        agent = AgentClass(model=model, env=env, **agent_kwargs)
    agent.extra_template_vars["hivemind_skills"] = chunks_text

    # 5) Run.
    try:
        result = agent.run(task=task.prompt)
        exit_status = result.get("exit_status", "")
        submission = result.get("submission", "")
        error = None
    except Exception as e:  # noqa: BLE001
        exit_status = type(e).__name__
        submission = ""
        error = str(e)

    # 6) Score via the optional test command.
    success = False
    if task.test_cmd:
        import subprocess

        cmd_result = subprocess.run(
            task.test_cmd, shell=True, cwd=task.work_dir, capture_output=True, timeout=120
        )
        success = cmd_result.returncode == 0

    # 7) Optional feedback to the policy (for System 3).
    if policy_name == "online_bandit":
        try:
            from hivemind.api import hub
            p = hub.get_or_create("online_bandit")
            if hasattr(p, "record_feedback"):
                p.record_feedback(task.id, success=success, cost_usd=float(agent.cost))
        except Exception:  # noqa: BLE001
            pass

    return HarnessResult(
        task_id=task.id,
        policy=synth.policy,
        model=req.model,
        success=success,
        exit_status=exit_status,
        cost_usd=float(agent.cost),
        n_calls=int(agent.n_calls),
        n_chunks=len(synth.chunks),
        chunk_ids=[c.skill_id for c in synth.chunks],
        error=error,
        submission=submission,
    )


# --- dynamic-injection variant --------------------------------------------

def _DynamicReinjectionAgent_cls():
    """Lazy import so we don't pay the cost when only static is used."""
    from minisweagent.agents.default import DefaultAgent

    class _DynamicReinjectionAgent(DefaultAgent):
        """Calls /synthesize on every step and appends new chunks as system messages.

        This is the integration that validates System 3's mid-trajectory injection.
        """

        def __init__(self, *args, _hivemind_adapter, _hivemind_task, _hivemind_budget, **kwargs):
            super().__init__(*args, **kwargs)
            self._hm_adapter = _hivemind_adapter
            self._hm_task = _hivemind_task
            self._hm_budget = _hivemind_budget
            self._hm_seen_skill_ids: set[str] = set()
            self._hm_turn = 0

        def step(self):
            # Re-synthesize against current message tail; inject *new* skills only.
            tail = [Message(role=m.get("role", "user"), content=m.get("content", "")) for m in self.messages[-6:]]
            synth = self._hm_adapter.inject(
                conversation=tail,
                model=str(getattr(getattr(self.model, "config", None), "model_name", "unknown")),
                budget_tokens=self._hm_budget,
                harness="mini-swe-agent",
                trajectory_id=self._hm_task.id,
                turn_index=self._hm_turn,
            )
            self._hm_turn += 1
            new_chunks = [c for c in synth.chunks if c.skill_id not in self._hm_seen_skill_ids]
            for c in new_chunks:
                self._hm_seen_skill_ids.add(c.skill_id)
                self.add_messages({"role": "system", "content": f"### Mid-trajectory skill: {c.skill_id}\n\n{c.content}"})
            return super().step()

    return _DynamicReinjectionAgent


_DynamicReinjectionAgent = _DynamicReinjectionAgent_cls()
