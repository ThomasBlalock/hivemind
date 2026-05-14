# Architecture

```
  agent harness ──► POST /synthesize ──► injection policy ──► skill chunks ──► agent ctx
                                              ▲                                    │
                                              │                                    ▼
                                      skills corpus                          agent runs task
                                      (versioned, audited)                         │
                                              ▲                                    ▼
                                              └────────── optional /feedback ──────┘
```

## Components

| Component | Role | Doc |
|---|---|---|
| Eval harness | Measure agent perf + cost on tasks | [evaluation/README.md](evaluation/README.md) |
| Agent harness | Run agents on tasks; hosts the injection hook | [agent_harness/README.md](agent_harness/README.md) |
| Skills corpus | Curated, audited, normalized skills | [skills_corpus/README.md](skills_corpus/README.md) |
| Injection policy | Chooses what to inject — the research target | [context_injection/README.md](context_injection/README.md) |
| Serving layer | HTTP API wrapping the policy | [serving/README.md](serving/README.md) |

## Data flow

1. Agent harness calls `POST /synthesize` with the conversation, model id, and token budget.
2. The active injection policy selects, orders, and (optionally) compresses skills from the corpus.
3. The harness splices response chunks into the agent's next prompt.
4. Optionally, the harness reports the outcome to `POST /feedback` — fuel for online-learning policies (see [context_injection/03_online_bandit.md](context_injection/03_online_bandit.md)).

API contract: [agent_harness/integration.md](agent_harness/integration.md).
