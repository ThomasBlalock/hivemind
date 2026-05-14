"""Name -> policy factory lookup."""

from __future__ import annotations

from typing import Callable

from hivemind.policies.base import Policy

_REGISTRY: dict[str, Callable[[], Policy]] = {}


def register_policy(name: str, factory: Callable[[], Policy]) -> None:
    _REGISTRY[name] = factory


def get_policy(name: str) -> Policy:
    if name not in _REGISTRY:
        raise KeyError(f"unknown policy: {name}. known: {sorted(_REGISTRY)}")
    return _REGISTRY[name]()


def list_policies() -> list[str]:
    return sorted(_REGISTRY)
