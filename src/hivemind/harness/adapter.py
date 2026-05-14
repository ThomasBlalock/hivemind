"""Adapter that turns a harness's prompt-building step into a /synthesize call.

Harnesses (OpenHands, Hermes, ...) plug into this single class. The harness
provides the current conversation; the adapter returns chunks to splice in.

See docs/agent_harness/integration.md for the contract.
"""

from __future__ import annotations

import os
from collections.abc import Iterable

import httpx

from hivemind.api import hub
from hivemind.policies.base import Message, SynthesizeRequest, SynthesizeResponse


class InProcessAdapter:
    """Direct call into the local policy hub. Use this in tests and when the
    harness runs in the same process as HiveMind."""

    def __init__(self, policy_name: str | None = None):
        self._policy_name = policy_name or os.environ.get("HIVEMIND_DEFAULT_POLICY", "hybrid_retrieval")

    def inject(
        self,
        conversation: Iterable[dict | Message],
        *,
        model: str,
        budget_tokens: int = 4000,
        harness: str = "unknown",
        trajectory_id: str | None = None,
        turn_index: int | None = None,
    ) -> SynthesizeResponse:
        conv = [m if isinstance(m, Message) else Message(**m) for m in conversation]
        req = SynthesizeRequest(
            conversation=conv,
            model=model,
            budget_tokens=budget_tokens,
            harness=harness,
            trajectory_id=trajectory_id,
            turn_index=turn_index,
        )
        return hub.get_or_create(self._policy_name).synthesize(req)


class HTTPAdapter:
    """Call out to a remote HiveMind /synthesize. Use in production harnesses."""

    def __init__(self, base_url: str = "http://localhost:8000", policy_name: str | None = None, timeout: float = 1.0):
        self._base = base_url.rstrip("/")
        self._policy_name = policy_name
        self._client = httpx.Client(timeout=timeout)

    def inject(
        self,
        conversation: Iterable[dict | Message],
        *,
        model: str,
        budget_tokens: int = 4000,
        harness: str = "unknown",
        trajectory_id: str | None = None,
        turn_index: int | None = None,
    ) -> SynthesizeResponse:
        conv = [m if isinstance(m, dict) else m.model_dump() for m in conversation]
        params = {"policy": self._policy_name} if self._policy_name else {}
        r = self._client.post(
            f"{self._base}/synthesize",
            params=params,
            json={
                "conversation": conv,
                "model": model,
                "budget_tokens": budget_tokens,
                "harness": harness,
                "trajectory_id": trajectory_id,
                "turn_index": turn_index,
            },
        )
        r.raise_for_status()
        return SynthesizeResponse(**r.json())
