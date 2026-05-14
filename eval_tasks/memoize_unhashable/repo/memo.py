from collections.abc import Callable
from functools import wraps
from typing import Any


def memoize(fn: Callable) -> Callable:
    """Cache fn's return values by (args, kwargs).

    Calls with unhashable arguments should NOT raise — they should fall back
    to recomputing and skip caching.
    """
    cache: dict[Any, Any] = {}

    @wraps(fn)
    def wrapper(*args, **kwargs):
        # BUG: TypeError leaks out when args contain unhashable items.
        key = (args, tuple(sorted(kwargs.items())))
        if key in cache:
            return cache[key]
        result = fn(*args, **kwargs)
        cache[key] = result
        return result

    return wrapper
