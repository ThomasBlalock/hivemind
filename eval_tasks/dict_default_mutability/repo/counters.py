def make_counter_table(keys: list[str], table: dict | None = {}) -> dict[str, int]:
    """Return a counter table mapping each key to 0.

    Bug: ``table={}`` is a mutable default, shared across all calls. The fix
    is the canonical "default to None, build a fresh dict inside the body".
    """
    if table is None:
        table = {}
    for k in keys:
        table.setdefault(k, 0)
    return table


def bump(table: dict[str, int], key: str) -> None:
    table[key] = table.get(key, 0) + 1
