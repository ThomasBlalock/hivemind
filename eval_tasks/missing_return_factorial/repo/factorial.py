def factorial(n: int) -> int:
    """Return n! for non-negative n. 0! is 1."""
    if n < 0:
        raise ValueError("n must be non-negative")
    if n <= 1:
        return 1
    return n * factorial(n - 1)
