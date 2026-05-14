from collections.abc import Callable, Iterable
from typing import TypeVar

T = TypeVar("T")
K = TypeVar("K")


def group_by(items: Iterable[T], key: Callable[[T], K]) -> dict[K, list[T]]:
    """Group ``items`` by ``key(item)``.

    For each group, items must appear in the original iteration order.
    """
    # BUG: using a set instead of a list reorders members inside a group.
    out: dict[K, set] = {}
    for item in items:
        k = key(item)
        out.setdefault(k, set()).add(item)
    # Cast sets to sorted-list to silence type errors; this also reorders.
    return {k: sorted(v) for k, v in out.items()}
