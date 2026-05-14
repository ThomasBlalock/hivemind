from pq import PriorityQueue


def test_priority_order():
    q = PriorityQueue()
    q.push("a", 3)
    q.push("b", 1)
    q.push("c", 2)
    assert [q.pop() for _ in range(3)] == ["b", "c", "a"]


def test_fifo_tie_break():
    q = PriorityQueue()
    q.push("first", 5)
    q.push("second", 5)
    q.push("third", 5)
    assert q.pop() == "first"
    assert q.pop() == "second"
    assert q.pop() == "third"


def test_unorderable_items_dont_crash():
    """dicts are not orderable; ties must NOT fall back to comparing them."""
    q = PriorityQueue()
    q.push({"id": 1}, 5)
    q.push({"id": 2}, 5)
    assert q.pop() == {"id": 1}
    assert q.pop() == {"id": 2}
