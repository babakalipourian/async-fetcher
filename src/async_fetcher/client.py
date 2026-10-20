from async_fetcher.config import FetcherConfig
from async_fetcher.models.request import FetchRequest
from async_fetcher.models.response import FetchResponse
from async_fetcher.services.fetcher import AsyncFetcher


class AsyncFetcherClient:
    """Public client interface for asynchronous HTTP fetching."""

    def __init__(self, config: FetcherConfig | None = None) -> None:
        self._fetcher = AsyncFetcher(config)

    async def fetch(self, request: FetchRequest) -> FetchResponse:
        """Fetch a single HTTP resource."""
        return await self._fetcher.fetch(request)

    async def fetch_many(
        self,
        requests: list[FetchRequest],
    ) -> list[FetchResponse | Exception]:
        """Fetch multiple HTTP resources concurrently."""
        return await self._fetcher.fetch_many(requests)

    async def aclose(self) -> None:
        """Close the client and release network resources."""
        await self._fetcher.aclose()

    async def __aenter__(self) -> "AsyncFetcherClient":
        await self._fetcher.__aenter__()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: object | None,
    ) -> None:
        await self._fetcher.__aexit__(exc_type, exc_value, traceback)
