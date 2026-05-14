"""Reference implementation of the OpenHands -> HiveMind injection patch.

This file is **not** wired into a real OpenHands install. It exists to show
what the patch should look like when you vendor OpenHands for real. See
docs/agent_harness/openhands.md.

The integration point in OpenHands is the microagent loader. In recent
OpenHands versions this lives roughly at:

    openhands/microagent/registry.py

The keyword-trigger match in that file becomes:

    from hivemind.harness.adapter import HTTPAdapter

    _hivemind = HTTPAdapter(
        base_url=os.environ.get("HIVEMIND_URL", "http://localhost:8000"),
        policy_name=os.environ.get("HIVEMIND_POLICY", "hybrid_retrieval"),
    )

    def get_active_microagents(event_stream, model_id, budget):
        resp = _hivemind.inject(
            conversation=_event_stream_to_messages(event_stream),
            model=model_id,
            budget_tokens=budget,
            harness="openhands",
            trajectory_id=event_stream.session_id,
            turn_index=event_stream.turn_count,
        )
        return [_chunk_to_microagent(c) for c in resp.chunks]

The two adapter functions (`_event_stream_to_messages`,
`_chunk_to_microagent`) are simple shape conversions and will live in this
file once we vendor.
"""
