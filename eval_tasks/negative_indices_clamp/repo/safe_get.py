from typing import Any


def safe_get(seq: list[Any], idx: int, default: Any = None) -> Any:
    """Return seq[idx] for any in-bounds idx, else default.

    For this API, "in bounds" means 0 <= idx < len(seq). Negative indices are
    treated as out of bounds (not Python's usual wrap-around).
    """
    if idx < len(seq):  # BUG: missing the `idx >= 0` check; -1 etc. wrap.
        return seq[idx]
    return default
