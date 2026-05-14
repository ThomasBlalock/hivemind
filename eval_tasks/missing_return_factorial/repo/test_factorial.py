import pytest

from factorial import factorial


def test_basic():
    assert factorial(0) == 1
    assert factorial(1) == 1
    assert factorial(5) == 120
    assert factorial(7) == 5040


def test_negative_raises():
    with pytest.raises(ValueError):
        factorial(-1)
