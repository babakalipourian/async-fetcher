import asyncio

import httpx
import structlog

from async_fetcher.config import FetcherConfig
from async_fetcher.exceptions import (
    FetcherClosedError,
    HTTPStatusError,
    RetryExhaustedError,
    TransportError,
)
from async_fetcher.models.request import FetchRequest
from async_fetcher.models.response import FetchResponse
from async_fetcher.services.concurrency import ConcurrencyLimiter
from async_fetcher.services.retry import RetryPolicy
from async_fetcher.transport.http import HTTPTransport

logger = structlog.get_logger(__name__)


class AsyncFetcher:
    """Fetch HTTP resources with bounded concurrency and retries."""

    def __init__(self, config: FetcherConfig | None = None) -> None:
        self._config = config or FetcherConfig()
        self._limiter = ConcurrencyLimiter(self._config.max_concurrency)
        self._retry_policy = RetryPolicy(self._config)
        self._transport = HTTPTransport(
            timeout=self._config.timeout,
            max_connections=self._config.max_connections,
            max_keepalive_connections=self._config.max_keepalive_connections,
            follow_redirects=self._config.follow_redirects,
        )
        self._closed = False

    async def fetch(self, request: FetchRequest) -> FetchResponse:
        """Fetch one URL, retrying eligible transient failures."""
        if self._closed:
            raise FetcherClosedError("AsyncFetcher is closed.")

        attempts = 0

        async def operation() -> FetchResponse:
            nonlocal attempts
            attempts += 1

            async with self._limiter:
                response = await self._transport.send(request)

            if self._config.raise_on_http_error and response.status_code >= 400:
                raise HTTPStatusError(
                    "HTTP response returned an error status.",
                    url=str(response.url),
                    method=request.method,
                    status_code=response.status_code,
                    response_body=response.body,
                )

            logger.info(
                "request_completed",
                url=str(response.url),
                method=request.method,
                status_code=response.status_code,
                attempt=attempts,
            )
            return response.model_copy(update={"attempts": attempts})

        def should_retry(exc: Exception) -> bool:
            if isinstance(exc, HTTPStatusError):
                return exc.status_code in {408, 429, 500, 502, 503, 504}
            return isinstance(exc, (TransportError, httpx.TransportError))

        try:
            return await self._retry_policy.execute(
                operation,
                should_retry=should_retry,
            )
        except (TransportError, HTTPStatusError) as exc:
            if attempts > 1:
                raise RetryExhaustedError(
                    "Request failed after retry attempts.",
                    url=str(request.url),
                    method=request.method,
                    attempts=attempts,
                    last_exception=exc,
                ) from exc
            raise

    async def fetch_many(
        self,
        requests: list[FetchRequest],
    ) -> list[FetchResponse | Exception]:
        """Fetch multiple requests concurrently, preserving input order."""
        if self._closed:
            raise FetcherClosedError("AsyncFetcher is closed.")

        return list(
            await asyncio.gather(*(self._fetch_safely(request) for request in requests))
        )

    async def _fetch_safely(
        self,
        request: FetchRequest,
    ) -> FetchResponse | Exception:
        try:
            return await self.fetch(request)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning(
                "request_failed",
                url=str(request.url),
                method=request.method,
                error_type=type(exc).__name__,
            )
            return exc

    async def aclose(self) -> None:
        """Release underlying HTTP resources."""
        if not self._closed:
            self._closed = True
            await self._transport.aclose()

    async def __aenter__(self) -> "AsyncFetcher":
        if self._closed:
            raise FetcherClosedError("AsyncFetcher is closed.")
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.aclose()
