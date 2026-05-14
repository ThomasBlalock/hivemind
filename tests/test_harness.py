from __future__ import annotations

from hivemind.harness.fake_harness import FakeHarness


def test_fake_harness_drives_injection(isolated_corpus):
    h = FakeHarness()
    traj = h.run(
        ["please bisect this regression", "what was the broken commit?"],
        trajectory_id="t-1",
    )
    assert len(traj.injected_chunks_per_turn) == 2
    # At least the bisect-related turn should produce a chunk.
    flat = [c for turn in traj.injected_chunks_per_turn for c in turn]
    assert any(c.skill_id == "git-bisect" for c in flat)
