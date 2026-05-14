from safe_get import safe_get


def test_in_bounds():
    assert safe_get([1, 2, 3], 0) == 1
    assert safe_get([1, 2, 3], 2) == 3


def test_out_of_bounds_returns_default():
    assert safe_get([1, 2, 3], 5) is None
    assert safe_get([1, 2, 3], 5, default="x") == "x"


def test_negative_is_out_of_bounds():
    # Should NOT wrap around. The expected behavior is "negative is out of bounds".
    assert safe_get([1, 2, 3], -1) is None
    assert safe_get([1, 2, 3], -3, default=42) == 42


def test_empty():
    assert safe_get([], 0) is None
