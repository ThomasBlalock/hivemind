"""FastAPI app. See docs/serving/api.md.

Endpoints:
- POST /synthesize?policy=<name>
- POST /feedback
- GET /policies
- GET /healthz
- GET /metrics
"""

from __future__ import annotations

import os
import time
from collections import Counter

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

# Ensure all policy modules get imported so they register.
import hivemind.policies.baseline  # noqa: F401
import hivemind.policies.dspy_compiled  # noqa: F401
import hivemind.policies.hybrid_retrieval  # noqa: F401
import hivemind.policies.online_bandit  # noqa: F401
from hivemind.api import hub
from hivemind.policies import SynthesizeRequest, SynthesizeResponse, list_policies

_DEFAULT_POLICY = os.environ.get("HIVEMIND_DEFAULT_POLICY", "hybrid_retrieval")

app = FastAPI(title="HiveMind", version="0.0.1")


_METRICS: dict[str, Counter] = {
    "synthesize_calls": Counter(),
    "synthesize_errors": Counter(),
    "feedback_calls": Counter(),
}


class FeedbackRequest(BaseModel):
    trajectory_id: str
    success: bool
    cost_usd: float = 0.0
    turns: int = 0


class FeedbackResponse(BaseModel):
    accepted: bool
    arms_updated: int


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok", "default_policy": _DEFAULT_POLICY}


@app.get("/policies")
def policies() -> dict:
    return {"available": list_policies(), "default": _DEFAULT_POLICY}


@app.get("/metrics")
def metrics() -> dict:
    return {k: dict(v) for k, v in _METRICS.items()}


@app.post("/synthesize", response_model=SynthesizeResponse)
def synthesize(
    req: SynthesizeRequest,
    policy: str = Query(default=None),
) -> SynthesizeResponse:
    name = policy or _DEFAULT_POLICY
    try:
        p = hub.get_or_create(name)
    except KeyError as e:
        _METRICS["synthesize_errors"][name] += 1
        raise HTTPException(status_code=404, detail=str(e)) from None  # noqa: B904
    t0 = time.perf_counter()
    resp = p.synthesize(req)
    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    # Server-measured latency overrides policy-reported, for honesty in metrics.
    resp = resp.model_copy(update={"latency_ms": elapsed_ms})
    _METRICS["synthesize_calls"][name] += 1
    return resp


@app.post("/feedback", response_model=FeedbackResponse)
def feedback(req: FeedbackRequest) -> FeedbackResponse:
    """Dispatch to any active policy that exposes ``record_feedback``."""
    updated = 0
    for name, p in hub.known_instances().items():
        if hasattr(p, "record_feedback"):
            try:
                updated += p.record_feedback(req.trajectory_id, req.success, req.cost_usd)
            except Exception:  # noqa: BLE001
                # A misbehaving policy should not break feedback for the others.
                continue
        _METRICS["feedback_calls"][name] += 1
    return FeedbackResponse(accepted=True, arms_updated=updated)
