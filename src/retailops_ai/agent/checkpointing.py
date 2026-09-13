"""Durable LangGraph checkpoint backends for RetailOps AI."""

from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from langgraph.checkpoint.memory import InMemorySaver


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class CheckpointerConfig:
    backend: str = "memory"
    dsn: str | None = None
    setup: bool = True

    def __post_init__(self) -> None:
        if self.backend not in {"memory", "postgres"}:
            raise ValueError("checkpointer backend must be memory or postgres")
        if self.backend == "postgres" and not self.dsn:
            raise ValueError("postgres checkpointer requires a DSN")

    @classmethod
    def from_env(cls) -> CheckpointerConfig:
        return cls(
            backend=os.getenv("AGENT_CHECKPOINTER_BACKEND", "memory").lower(),
            dsn=os.getenv("AGENT_CHECKPOINTER_DSN") or None,
            setup=_env_bool("AGENT_CHECKPOINTER_SETUP", True),
        )


@dataclass
class CheckpointerHandle:
    saver: Any
    backend: str
    durable: bool
    _close_callback: Callable[[], None] | None = None
    _closed: bool = False

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._close_callback is not None:
            self._close_callback()


def open_checkpointer(config: CheckpointerConfig) -> CheckpointerHandle:
    if config.backend == "memory":
        return CheckpointerHandle(
            saver=InMemorySaver(),
            backend="memory",
            durable=False,
        )

    from langgraph.checkpoint.postgres import PostgresSaver

    manager = PostgresSaver.from_conn_string(config.dsn or "")
    saver = manager.__enter__()
    try:
        if config.setup:
            saver.setup()
    except Exception:
        manager.__exit__(None, None, None)
        raise

    return CheckpointerHandle(
        saver=saver,
        backend="postgres",
        durable=True,
        _close_callback=lambda: manager.__exit__(None, None, None),
    )
