import time

from window_avg import sliding_window_avg


def test_basic():
    assert sliding_window_avg([1, 2, 3, 4, 5], 3) == [2.0, 3.0, 4.0]


def test_k_equals_len():
    assert sliding_window_avg([1, 2, 3], 3) == [2.0]


def test_k_greater_than_len_returns_empty():
    assert sliding_window_avg([1, 2], 5) == []


def test_k_non_positive_returns_empty():
    assert sliding_window_avg([1, 2, 3], 0) == []
    assert sliding_window_avg([1, 2, 3], -1) == []


def test_linear_time_complexity():
    """A naive O(n*k) impl with n=200_000 and k=100 would take seconds.
    The O(n) prefix-sum impl finishes in well under a second."""
    n, k = 200_000, 100
    xs = [float(i) for i in range(n)]
    t0 = time.perf_counter()
    out = sliding_window_avg(xs, k)
    elapsed = time.perf_counter() - t0
    assert len(out) == n - k + 1
    assert elapsed < 1.0, f"too slow: {elapsed:.2f}s"
