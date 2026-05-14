def sliding_window_avg(xs: list[float], k: int) -> list[float]:
    """Return the average of every contiguous k-length window in xs.

    Output length: max(0, len(xs) - k + 1).
    Should run in O(n) time. Empty list if k > len(xs) or k <= 0.
    """
    # BUG 1: O(n*k) nested-loop implementation.
    # BUG 2: when k > len(xs), `range(len(xs) - k + 1)` is range(-x) which
    #        is empty in Python — but then we still divide by k below, which
    #        is fine; the real issue is k <= 0 isn't guarded.
    out: list[float] = []
    for i in range(len(xs) - k + 1):
        s = 0.0
        for j in range(i, i + k):
            s += xs[j]
        out.append(s / k)
    return out
