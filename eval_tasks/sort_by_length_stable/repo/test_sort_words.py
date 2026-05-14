from sort_words import sort_by_length


def test_basic():
    out = sort_by_length(["aaa", "b", "cc", "ddd", "e"])
    assert out == ["b", "e", "cc", "aaa", "ddd"]


def test_all_same_length_preserves_order():
    out = sort_by_length(["cat", "bat", "rat", "hat"])
    assert out == ["cat", "bat", "rat", "hat"]


def test_two_groups_preserve_order_per_group():
    out = sort_by_length(["abcd", "ab", "wxyz", "yz", "mn"])
    assert out == ["ab", "yz", "mn", "abcd", "wxyz"]
