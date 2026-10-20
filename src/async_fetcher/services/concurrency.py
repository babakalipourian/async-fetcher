import asyncio


class ConcurrencyLimiter:
    """Limit the number of concurrent operations."""

    def __init__(self, limit: int) -> None:
        if limit < 1:
            raise ValueError("Concurrency limit must be at least 1.")

        self._semaphore = asyncio.Semaphore(limit)
        self._limit = limit

    @property
    def limit(self) -> int:
        """Return the configured concurrency limit."""
        return self._limit

    async def __aenter__(self) -> "ConcurrencyLimiter":
        await self._semaphore.acquire()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: object | None,
    ) -> None:
        self._semaphore.release()
