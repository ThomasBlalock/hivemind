from group_by import group_by


def test_basic():
    out = group_by([1, 2, 3, 4, 5, 6], lambda n: n % 2)
    assert out == {1: [1, 3, 5], 0: [2, 4, 6]}


def test_order_preserved_within_group():
    # Insertion order ≠ sorted order, so a sort-based impl will fail here.
    out = group_by(["zebra", "apple", "yak", "ant"], lambda s: s[0])
    assert out["z"] == ["zebra"]
    assert out["a"] == ["apple", "ant"]
    assert out["y"] == ["yak"]


def test_duplicates_kept_within_group():
    # A set would collapse duplicates; a list keeps them.
    out = group_by([1, 1, 2, 1, 2], lambda n: n % 2)
    assert out[1] == [1, 1, 1]
    assert out[0] == [2, 2]


def test_empty():
    assert group_by([], lambda x: x) == {}
