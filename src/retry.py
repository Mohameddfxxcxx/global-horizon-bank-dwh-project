"""Retry utilities for resilient external-system calls.

The ``retry`` decorator implements bounded retry with exponential backoff and
jitter. It is intended for transient failures (network, deadlocks, throttling),
not for logic errors — those should surface immediately.
"""

from __future__ import annotations

import functools
import random
import time
from collections.abc import Callable
from typing import TypeVar

from .logger import get_logger

T = TypeVar("T")
_log = get_logger(__name__)


def retry(
    *,
    attempts: int = 3,
    delay: float = 0.5,
    backoff: float = 2.0,
    jitter: float = 0.2,
    exceptions: tuple[type[BaseException], ...] = (Exception,),
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Retry a callable on transient failures with exponential backoff."""

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: object, **kwargs: object) -> T:
            current = delay
            last_exc: BaseException | None = None
            for attempt in range(1, attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    last_exc = exc
                    if attempt == attempts:
                        _log.error(
                            "retry_exhausted func=%s attempts=%d error=%s",
                            func.__name__, attempts, exc,
                        )
                        raise
                    sleep_for = current + random.uniform(0, jitter)
                    _log.warning(
                        "retry_attempt func=%s attempt=%d/%d sleep=%.2fs error=%s",
                        func.__name__, attempt, attempts, sleep_for, exc,
                    )
                    time.sleep(sleep_for)
                    current *= backoff
            assert last_exc is not None
            raise last_exc  # unreachable, but keeps type-checkers happy

        return wrapper

    return decorator
