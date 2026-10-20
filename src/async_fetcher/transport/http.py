import time
from types import MappingProxyType

import httpx

from async_fetcher.exceptions import TransportError
from async_fetcher.models.request import FetchRequest
from async_fetcher.models.response import FetchResponse


class HTTPTransport:
    """Asynchronous HTTP transport with explicit client lifecycle."""

    def __init__(
        self,
        *,
        timeout: float,
        max_connections: int,
        max_keepalive_connections: int,
        follow_redirects: bool = True,
    ) -> None:
        self._client = httpx.AsyncClient(
            timeout=timeout,
            limits=httpx.Limits(
                max_connections=max_connections,
                max_keepalive_connections=max_keepalive_connections,
            ),
            follow_redirects=follow_redirects,
        )
        self._closed = False

    async def send(self, request: FetchRequest) -> FetchResponse:
        """Send one HTTP request and validate its response."""
        if self._closed:
            raise RuntimeError("HTTPTransport is closed.")

        started_at = time.perf_counter()

        try:
            response = await self._client.request(
                method=request.method,
                url=str(request.url),
                headers=dict(request.headers),
                params=dict(request.params),
                timeout=request.timeout,
            )
        except httpx.TimeoutException as exc:
            raise TransportError(
                "HTTP request timed out.",
                url=str(request.url),
                method=request.method,
            ) from exc
        except httpx.RequestError as exc:
            raise TransportError(
                "HTTP request failed.",
                url=str(request.url),
                method=request.method,
            ) from exc

        elapsed = time.perf_counter() - started_at

        return FetchResponse(
            url=str(response.url),
            status_code=response.status_code,
            headers=MappingProxyType(dict(response.headers)),
            body=response.content,
            elapsed_seconds=elapsed,
            attempts=1,
        )

    async def aclose(self) -> None:
        """Close the underlying HTTP client."""
        if not self._closed:
            self._closed = True
            await self._client.aclose()

    async def __aenter__(self) -> "HTTPTransport":
        if self._closed:
            raise RuntimeError("HTTPTransport is closed.")
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.aclose()
