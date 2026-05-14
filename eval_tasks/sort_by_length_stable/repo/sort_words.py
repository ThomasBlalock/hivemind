def sort_by_length(words: list[str]) -> list[str]:
    """Sort words by length, breaking ties by original insertion order.

    For two words with the same length, the one that appeared earlier in the
    input must appear earlier in the output.
    """
    # BUG: comparing (len, hash(word)) is not stable in tie-order and not even
    # deterministic across runs. Should rely on Python's stable sort instead.
    return sorted(words, key=lambda w: (len(w), hash(w)))
