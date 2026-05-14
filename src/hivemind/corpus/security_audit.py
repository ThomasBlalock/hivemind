"""Automated security audit for skills before ingestion.

See docs/skills_corpus/security_audit.md. This module implements the
pattern-match layer only; model-graded checks and manual review are tracked
separately.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Patterns that indicate prompt-injection or data-exfiltration intent.
# Conservative — false positives go to manual review, not auto-fail.
_RISKY_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("override_system_prompt", re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions", re.I)),
    ("exfiltrate_secrets", re.compile(r"(send|post|upload|exfiltrate).{0,40}(api[\s_-]*key|secret|token|password|\benv\b)", re.I)),
    ("runtime_fetch", re.compile(r"(curl|wget|fetch|requests\.get)\s+https?://", re.I)),
    ("eval_arbitrary", re.compile(r"\beval\s*\(", re.I)),
    ("exec_arbitrary", re.compile(r"\bexec\s*\(", re.I)),
    ("shell_pipe_to_sh", re.compile(r"\|\s*(ba)?sh\b", re.I)),
    ("system_prompt_marker", re.compile(r"</?system[> ]", re.I)),
]


@dataclass
class AuditReport:
    status: str  # "passed" | "failed" | "manual_review_required"
    notes: list[str]


def audit_body(body: str) -> AuditReport:
    """Pattern-match audit. Returns hits as audit notes."""
    hits = [name for name, pat in _RISKY_PATTERNS if pat.search(body)]
    if not hits:
        return AuditReport(status="passed", notes=[])
    # Distinguish hard-fail patterns (clear exfiltration / override) from
    # "looks risky, get a human".
    hard_fail = {"override_system_prompt", "exfiltrate_secrets"}
    if any(h in hard_fail for h in hits):
        return AuditReport(status="failed", notes=[f"matched:{h}" for h in hits])
    return AuditReport(
        status="manual_review_required",
        notes=[f"matched:{h}" for h in hits],
    )
