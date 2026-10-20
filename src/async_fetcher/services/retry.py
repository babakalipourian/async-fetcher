import asyncio
import random
from collections.abc import Awaitable, Callable
from typing import TypeVar

from async_fetcher.config import FetcherConfig

T = TypeVar("T")


class RetryPolicy:
    """Execute asynchronous operations with exponential backoff."""

    def __init__(self, config: FetcherConfig) -> None:
        self._max_retries = config.max_retries
        self._backoff_factor = config.backoff_factor
        self._max_backoff = config.max_backoff

    async def execute(
        self,
        operation: Callable[[], Awaitable[T]],
        *,
        should_retry: Callable[[Exception], bool],
    ) -> T:
        """Retry eligible failures with capped exponential backoff."""
        for attempt in range(self._max_retries + 1):
            try:
                return await operation()
            except Exception as exc:
                if attempt >= self._max_retries or not should_retry(exc):
                    raise

                delay = min(
                    self._backoff_factor * (2**attempt),
                    self._max_backoff,
                )

                if delay > 0:
                    delay *= random.uniform(0.8, 1.2)
                    delay = min(delay, self._max_backoff)

                await asyncio.sleep(delay)

        raise RuntimeError("Retry loop exited unexpectedly.")
