"""Singleton-per-name policy cache + feedback fan-out.

We want one instance of each policy (they hold indexes, state, caches), but
we don't want every /synthesize call to rebuild the index.
"""

from __future__ import annotations

from threading import Lock

from hivemind.policies import get_policy
from hivemind.policies.base import Policy

_INSTANCES: dict[str, Policy] = {}
_LOCK = Lock()


def get_or_create(name: str) -> Policy:
    with _LOCK:
        if name not in _INSTANCES:
            _INSTANCES[name] = get_policy(name)
        return _INSTANCES[name]


def known_instances() -> dict[str, Policy]:
    with _LOCK:
        return dict(_INSTANCES)


def reset() -> None:
    """For tests."""
    with _LOCK:
        _INSTANCES.clear()
