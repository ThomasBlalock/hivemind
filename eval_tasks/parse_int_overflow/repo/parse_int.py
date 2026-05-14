def parse_uint16(s: str) -> int:
    """Parse a string into an unsigned 16-bit int (0..65535).

    Raises ValueError if the input is not numeric or out of range.
    """
    # BUG: only the int() conversion's own ValueError is propagated. There is
    # no bounds check, so values < 0 or > 65535 are accepted silently.
    return int(s)
