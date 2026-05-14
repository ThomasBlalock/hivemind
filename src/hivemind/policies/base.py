"""Shared types for the /synthesize contract.

See docs/agent_harness/integration.md for the request/response rationale.
"""

from __future__ import annotations

from typing import Literal, Protocol

from pydantic import BaseModel, Field

Position = Literal["system_suffix", "pre_tools", "last_user_prefix"]


class Message(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: str
    tool_calls: list[dict] | None = None


class SynthesizeRequest(BaseModel):
    conversation: list[Message]
    model: str
    budget_tokens: int = Field(ge=0)
    harness: str | None = None
    trajectory_id: str | None = None
    turn_index: int | None = None


class Chunk(BaseModel):
    content: str
    position: Position
    skill_id: str
    source_sha: str
    score: float | None = None


class SynthesizeResponse(BaseModel):
    chunks: list[Chunk]
    policy: str
    tokens: int
    latency_ms: int


class Policy(Protocol):
    name: str

    def synthesize(self, req: SynthesizeRequest) -> SynthesizeResponse:
        ...
