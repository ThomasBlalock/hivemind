import heapq
from typing import Any


class PriorityQueue:
    """A min-priority queue with stable FIFO tie-breaking.

    push(item, priority); pop() -> item. Lower priority pops first. Among
    equal-priority items the one pushed first pops first.
    """

    def __init__(self):
        # BUG: this stores (priority, item) tuples. When two priorities tie,
        # heapq compares ``item`` next, which raises TypeError for dicts or
        # other unorderable types, and otherwise breaks ties by item ordering
        # instead of insertion order.
        self._heap: list[tuple[int, Any]] = []

    def push(self, item: Any, priority: int) -> None:
        heapq.heappush(self._heap, (priority, item))

    def pop(self) -> Any:
        return heapq.heappop(self._heap)[1]

    def __len__(self) -> int:
        return len(self._heap)
