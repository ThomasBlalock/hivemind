from memo import memoize


def test_basic_caches_hashable_args():
    calls = []

    @memoize
    def f(x: int) -> int:
        calls.append(x)
        return x * 2

    assert f(3) == 6
    assert f(3) == 6
    assert calls == [3]


def test_unhashable_args_dont_raise():
    """A list arg is unhashable — must not raise, must still return the result."""
    calls = []

    @memoize
    def sum_of(items: list[int]) -> int:
        calls.append(items)
        return sum(items)

    # First call.
    assert sum_of([1, 2, 3]) == 6
    # Second call with an equal but distinct list; allowed to recompute, must
    # not crash.
    assert sum_of([1, 2, 3]) == 6


def test_dict_kwarg_doesnt_raise():
    @memoize
    def merge(**kwargs):
        return dict(kwargs)

    # Unhashable kwarg value — must not raise.
    assert merge(a={"x": 1}) == {"a": {"x": 1}}
