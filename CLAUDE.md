# HiveMind: Dynamic Context Optimization Hub

## Problem Definition
Current LLM capability expansion via skills files relies on naive text injection—statically appending documentation or using basic keyword-to-markdown mappings. This approach suffers from critical inefficiencies:
* **Context Dilution:** Bloating context windows degrades model attention precision ("lost-in-the-middle" effects) and inflates token latency/costs quadratically.
* **Static Sub-Optimality:** Context files are written for human legibility, lacking the mathematically optimal sequence of tokens tailored to a specific task, target model architecture, and execution state.
* **Friction & Stagnation:** Users must manually curate and inject context per workflow, completely bypassing cross-session network effects and automated feedback loops that could evolve context-injection methods effectiveness over time.

## Project Definition
A centralized, low-latency runtime Context Synthesis Layer that dynamically compiles and serves the optimal sequence of pre-generation tokens (skills, instructions, and tool schemas) directly into an LLM's reasoning context. A natural extension of Skill Retrieval Augmentation (SRA) frameworks.

## Implimentation Plan
1. Build a service that accepts a conversation and outputs the optimal context to inject into the thinking workflow of the agent to maximize the agent's performance.
2. Integrate the service into agent harnesses.

## Phases
1. Adopt a testing harness to evaluate the performance of agents on a variety of tasks, focusing on conding tasks. Track cost.
2. Adopt an agent harness and integrate a modular context injection method.
3. Select a large number of popular and effective skill files.
4. Test the most popular models in the agent harness with and without skills to establish a baseline.
5. Build a few context injection systems based on the corpa of selected skills that we think will beat the basic keyword trigger system used currently (bonus points if the system uses the results of the workflow to train itself in a feedback loop).
6. Test the context injection systems against our baselines, measuring any additional cost against added performance.
7. Repeat until a mid-tier model using a context injection technique performs as well a top-tier model.

## End State
A pretty graph (like the ones used in all model release papers) showing that you can get elite performance for half the cost using this system. People are compelled to try it out for themselves by ditching their skills system and hooking up to our endpoint instead. It works well and open source projects like Hermes add our endpoint as an integration, and add the context injection system into their agent harness. We become a class of models in agent harnesses used for context injection.

## Constraints
- Audit all additions to the skills corpa to ensure security.
- Uses secure software release infrastructure. Publically auditable and open, so that developers can be confident that the system is secure and there is no risk of adverse prompt injection.
- Low cost and latency compared to foundation models.

## Documentation

Full design lives under `docs/`. The implementation plan with checkboxes is `todo/plan.md`. Start with the entry below that matches what you're touching.

| If you're modifying... | Look at this first |
|---|---|
| Project-wide architecture or data flow | `@docs/architecture.md` |
| The evaluation harness (Inspect AI, benchmarks, cost) | `@docs/evaluation/README.md` |
| The reporting pipeline (sweep CSV → markdown + perf-vs-cost chart) | `@docs/evaluation/reporting.md` |
| Agent harness integration (OpenHands, Hermes, API contract) | `@docs/agent_harness/README.md` |
| The skills corpus (sources, ingestion, audit) | `@docs/skills_corpus/README.md` |
| A context injection policy | `@docs/context_injection/README.md` |
| The basic hybrid-retrieval policy (System 1) | `@docs/context_injection/01_hybrid_retrieval.md` |
| The DSPy-compiled policy (System 2) | `@docs/context_injection/02_dspy_compiled_skills.md` |
| The online-bandit policy (System 3) | `@docs/context_injection/03_online_bandit.md` |
| The serving API or release process | `@docs/serving/README.md` |
| Terminology you don't recognize | `@docs/glossary.md` |
| The phased implementation plan | `@todo/plan.md` |
| The doc index itself | `@docs/README.md` |