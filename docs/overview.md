# Overview

> Canonical project definition: [../CLAUDE.md](../CLAUDE.md). This is a navigation summary.

## What HiveMind is

A low-latency runtime service that, given a conversation, returns the optimal sequence of pre-generation tokens (skills, instructions, tool schemas) to inject into an LLM's context.

## Why it exists

- Static skill files are written for humans, not for any specific (task, model, state) triple.
- Naive keyword triggers both miss real signal (paraphrase, synonym, multi-turn) and over-fire (bloating context, hurting attention).
- A centralized, learned system can improve across sessions and harnesses; static configs cannot.

## End state

A perf-vs-cost graph showing **mid-tier model + HiveMind ≈ top-tier model bare**, compelling enough that open agent projects (e.g. Hermes) integrate the endpoint by default.

## How we get there

See [architecture.md](architecture.md) for components, [../todo/plan.md](../todo/plan.md) for phased work, and [context_injection/README.md](context_injection/README.md) for the research target.
