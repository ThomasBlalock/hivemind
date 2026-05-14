"""Token counting. Uses tiktoken cl100k_base as a model-agnostic proxy.

Real per-model counts differ, but cl100k is accurate enough for budget packing
within ~10%, which is well inside the 10% headroom we reserve.
"""

from __future__ import annotations

from functools import lru_cache


@lru_cache(maxsize=1)
def _encoder():
    import tiktoken
    return tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    return len(_encoder().encode(text))
