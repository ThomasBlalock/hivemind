"""Canonical skill schema. See docs/skills_corpus/ingestion.md."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

AuditStatus = Literal["passed", "failed", "manual_review_required"]


class Skill(BaseModel):
    id: str
    title: str
    description: str
    triggers: list[str] = Field(default_factory=list)
    body: str
    source: str
    tokens: int
    audit_status: AuditStatus = "manual_review_required"
    audit_notes: list[str] = Field(default_factory=list)
