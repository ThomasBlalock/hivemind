from counters import bump, make_counter_table


def test_each_call_returns_independent_table():
    a = make_counter_table(["x", "y"])
    bump(a, "x")
    bump(a, "x")
    b = make_counter_table(["x"])
    assert b["x"] == 0, f"second call should be fresh, got {b}"


def test_basic_values():
    t = make_counter_table(["a", "b"])
    assert t == {"a": 0, "b": 0}
