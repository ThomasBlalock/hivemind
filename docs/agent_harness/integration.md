# Injection-point contract

The single API the harnesses speak to. Stable across policies; policy versioning is in the response.

## Request

```
POST /synthesize
{
  "conversation": [...],                 // OpenAI-style messages
  "model": "anthropic/claude-sonnet-4-6",
  "budget_tokens": 4000,
  "harness": "openhands",
  "trajectory_id": "uuid",               // optional; required for feedback
  "turn_index": 3                        // optional; lets the policy detect mid-trajectory calls
}
```

## Response

```
{
  "chunks": [
    {"content": "...", "position": "system_suffix", "skill_id": "git-bisect", "source_sha": "abc123"},
    ...
  ],
  "policy": "hybrid_retrieval@v1",
  "tokens": 1834,
  "latency_ms": 142
}
```

`position` ∈ `{system_suffix, pre_tools, last_user_prefix}`.

## Feedback (optional)

```
POST /feedback
{"trajectory_id": "uuid", "success": true, "cost_usd": 0.42, "turns": 8}
```

Consumed by [System 3](../context_injection/03_online_bandit.md). Other policies ignore it.

Implementation: `src/api/`. Full API: [../serving/api.md](../serving/api.md).
