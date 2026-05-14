"""Side-by-side comparison of all policies on the toy corpus.

Runs offline against the stub embedder/reranker — no API spend. The point
isn't to claim a quality result (a 3-skill toy corpus + stub backends can't);
it's to visibly confirm each policy is wired correctly end-to-end.

Run:
    python scripts/compare_policies.py
"""

from __future__ import annotations

import json

# Import for side-effect policy registration.
import hivemind.policies.baseline  # noqa: F401
import hivemind.policies.dspy_compiled  # noqa: F401
import hivemind.policies.hybrid_retrieval  # noqa: F401
import hivemind.policies.online_bandit  # noqa: F401
from hivemind.api import hub
from hivemind.policies.base import Message, SynthesizeRequest

QUERIES = [
    "I bisected a regression and found the bad commit; what now?",
    "AttributeError: 'NoneType' object has no attribute 'group' — help me debug",
    "Write a regex that matches ISO 8601 dates",
    "What's a good lunch place in tokyo",  # should miss all skills
]

POLICIES = ["baseline_a", "baseline_b", "hybrid_retrieval", "dspy_compiled", "online_bandit"]


def main() -> None:
    rows = []
    for q in QUERIES:
        for name in POLICIES:
            p = hub.get_or_create(name)
            req = SynthesizeRequest(
                conversation=[Message(role="user", content=q)],
                model="claude-sonnet-4-6",
                budget_tokens=2000,
                trajectory_id=f"demo-{name}-{abs(hash(q)) % 10000}",
            )
            r = p.synthesize(req)
            rows.append(
                {
                    "query": q[:50],
                    "policy": r.policy,
                    "n_chunks": len(r.chunks),
                    "tokens": r.tokens,
                    "latency_ms": r.latency_ms,
                    "chunks": [c.skill_id for c in r.chunks],
                }
            )

    print(f"{'query':<52} {'policy':<22} {'n':>2} {'tokens':>7} {'latency_ms':>11}  chunks")
    print("-" * 130)
    for r in rows:
        print(
            f"{r['query']:<52} {r['policy']:<22} {r['n_chunks']:>2} "
            f"{r['tokens']:>7} {r['latency_ms']:>11}  {','.join(r['chunks'])}"
        )

    # Also dump as JSON for downstream tooling.
    out = {"results": rows}
    print()
    print(json.dumps(out, indent=2)[:2000] + ("\n..." if len(json.dumps(out)) > 2000 else ""))


if __name__ == "__main__":
    main()
