import httpx
import pytest
import respx

from async_fetcher import (
    AsyncFetcherError,
    FetcherClosedError,
    FetcherConfig,
    FetchRequest,
    HTTPStatusError,
    RetryExhaustedError,
    TransportError,
)
from async_fetcher.services.fetcher import AsyncFetcher


@pytest.mark.asyncio
@respx.mock
async def test_fetch_returns_response() -> None:
    respx.get("https://example.com/api").mock(
        return_value=httpx.Response(200, content=b"ok")
    )

    async with AsyncFetcher() as fetcher:
        response = await fetcher.fetch(FetchRequest(url="https://example.com/api"))

    assert response.status_code == 200
    assert response.body == b"ok"
    assert response.attempts == 1


@pytest.mark.asyncio
@respx.mock
async def test_fetch_many_preserves_order() -> None:
    respx.get("https://example.com/first").mock(
        return_value=httpx.Response(200, content=b"first")
    )
    respx.get("https://example.com/second").mock(
        return_value=httpx.Response(201, content=b"second")
    )

    async with AsyncFetcher() as fetcher:
        results = await fetcher.fetch_many(
            [
                FetchRequest(url="https://example.com/first"),
                FetchRequest(url="https://example.com/second"),
            ]
        )

    assert len(results) == 2
    assert results[0].status_code == 200  # type: ignore[union-attr]
    assert results[1].status_code == 201  # type: ignore[union-attr]


@pytest.mark.asyncio
@respx.mock
async def test_fetch_many_returns_exception_for_failed_request() -> None:
    respx.get("https://example.com/good").mock(
        return_value=httpx.Response(200, content=b"ok")
    )
    respx.get("https://example.com/bad").mock(
        side_effect=httpx.ConnectError("Connection failed")
    )

    async with AsyncFetcher() as fetcher:
        results = await fetcher.fetch_many(
            [
                FetchRequest(url="https://example.com/good"),
                FetchRequest(url="https://example.com/bad"),
            ]
        )

    assert len(results) == 2
    assert not isinstance(results[0], Exception)
    assert isinstance(results[1], Exception)


@pytest.mark.asyncio
@respx.mock
async def test_http_error_is_returned_when_raise_on_http_error_disabled() -> None:
    respx.get("https://example.com/not-found").mock(
        return_value=httpx.Response(404, content=b"not found")
    )

    config = FetcherConfig(raise_on_http_error=False)

    async with AsyncFetcher(config) as fetcher:
        response = await fetcher.fetch(
            FetchRequest(url="https://example.com/not-found")
        )

    assert response.status_code == 404


@pytest.mark.asyncio
@respx.mock
async def test_http_error_is_raised_when_enabled() -> None:
    respx.get("https://example.com/not-found").mock(
        return_value=httpx.Response(404, content=b"not found")
    )

    config = FetcherConfig(
        raise_on_http_error=True,
        max_retries=0,
    )

    async with AsyncFetcher(config) as fetcher:
        with pytest.raises(HTTPStatusError) as error:
            await fetcher.fetch(FetchRequest(url="https://example.com/not-found"))

    assert error.value.status_code == 404


@pytest.mark.asyncio
@respx.mock
async def test_transient_http_error_is_retried() -> None:
    route = respx.get("https://example.com/retry")
    route.side_effect = [
        httpx.Response(503),
        httpx.Response(200, content=b"ok"),
    ]

    config = FetcherConfig(
        raise_on_http_error=True,
        max_retries=1,
        backoff_factor=0,
    )

    async with AsyncFetcher(config) as fetcher:
        response = await fetcher.fetch(FetchRequest(url="https://example.com/retry"))

    assert response.status_code == 200
    assert response.attempts == 2
    assert route.call_count == 2


@pytest.mark.asyncio
@respx.mock
async def test_retry_exhaustion_is_reported() -> None:
    route = respx.get("https://example.com/unavailable").mock(
        return_value=httpx.Response(503)
    )

    config = FetcherConfig(
        raise_on_http_error=True,
        max_retries=1,
        backoff_factor=0,
    )

    async with AsyncFetcher(config) as fetcher:
        with pytest.raises(RetryExhaustedError) as error:
            await fetcher.fetch(FetchRequest(url="https://example.com/unavailable"))

    assert error.value.attempts == 2
    assert route.call_count == 2


@pytest.mark.asyncio
async def test_fetch_after_close_is_rejected() -> None:
    fetcher = AsyncFetcher()
    await fetcher.aclose()

    with pytest.raises(FetcherClosedError):
        await fetcher.fetch(FetchRequest(url="https://example.com"))


@pytest.mark.asyncio
async def test_fetch_many_after_close_is_rejected() -> None:
    fetcher = AsyncFetcher()
    await fetcher.aclose()

    with pytest.raises(FetcherClosedError):
        await fetcher.fetch_many([FetchRequest(url="https://example.com")])


@pytest.mark.asyncio
async def test_close_is_idempotent() -> None:
    fetcher = AsyncFetcher()

    await fetcher.aclose()
    await fetcher.aclose()


@pytest.mark.asyncio
@respx.mock
async def test_fetch_many_handles_cancellation() -> None:
    route = respx.get("https://example.com/slow").mock(
        side_effect=httpx.ConnectTimeout("Timed out")
    )

    config = FetcherConfig(max_retries=0)

    async with AsyncFetcher(config) as fetcher:
        results = await fetcher.fetch_many(
            [FetchRequest(url="https://example.com/slow")]
        )

    assert route.call_count == 1
    assert len(results) == 1
    assert isinstance(results[0], (TransportError, AsyncFetcherError))


@pytest.mark.asyncio
async def test_fetcher_context_manager_closes_resources() -> None:
    fetcher = AsyncFetcher()

    async with fetcher:
        pass

    with pytest.raises(FetcherClosedError):
        await fetcher.fetch(FetchRequest(url="https://example.com"))


@pytest.mark.asyncio
@respx.mock
async def test_fetch_many_respects_concurrency_limit() -> None:
    import asyncio

    limit = 2
    active = 0
    peak_active = 0

    async def delayed_response(request: httpx.Request) -> httpx.Response:
        nonlocal active, peak_active

        active += 1
        peak_active = max(peak_active, active)

        try:
            await asyncio.sleep(0.02)
            return httpx.Response(200, content=b"ok")
        finally:
            active -= 1

    for index in range(5):
        respx.get(f"https://example.com/{index}").mock(side_effect=delayed_response)

    config = FetcherConfig(
        max_concurrency=limit,
        max_connections=limit,
        max_keepalive_connections=limit,
        max_retries=0,
    )

    requests = [FetchRequest(url=f"https://example.com/{index}") for index in range(5)]

    async with AsyncFetcher(config) as fetcher:
        results = await fetcher.fetch_many(requests)

    assert len(results) == 5
    assert all(not isinstance(result, Exception) for result in results)
    assert peak_active == limit
    assert active == 0
