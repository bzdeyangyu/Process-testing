from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable


class HookRegistry:
    def __init__(self) -> None:
        self._hooks: dict[str, list[Callable[..., Any]]] = defaultdict(list)

    def register(self, hook_name: str, fn: Callable[..., Any]) -> None:
        self._hooks[hook_name].append(fn)

    def fire(self, hook_name: str, *args, **kwargs) -> list[Any]:
        return [fn(*args, **kwargs) for fn in self._hooks[hook_name]]
