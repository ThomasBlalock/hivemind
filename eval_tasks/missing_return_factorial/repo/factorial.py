def factorial(n: int) -> int:
    """Return n! for non-negative n. 0! is 1."""
    if n < 0:
        raise ValueError("n must be non-negative")
    if n <= 1:
        return 1
    # BUG: missing `return` keyword on the recursive call.
    n * factorial(n - 1)
