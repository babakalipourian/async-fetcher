import httpx
import pytest
import respx

from async_fetcher import (
    AsyncFetcherClient,
    FetcherConfig,
    FetchRequest,
    RetryExhaustedError,
)


@pytest.mark.asyncio
@respx.mock
async def test_fetch_request_end_to_end() -> None:
    respx.get("https://example.com/api").mock(
        return_value=httpx.Response(
            200,
            json={"status": "success"},
        )
    )

    async with AsyncFetcherClient() as client:
        response = await client.fetch(FetchRequest(url="https://example.com/api"))

    assert response.status_code == 200
    assert response.attempts == 1
    assert b"success" in response.body


@pytest.mark.asyncio
@respx.mock
async def test_retry_then_success_end_to_end() -> None:
    route = respx.get("https://example.com/retry")
    route.side_effect = [
        httpx.Response(503),
        httpx.Response(200, json={"ok": True}),
    ]

    config = FetcherConfig(
        raise_on_http_error=True,
        max_retries=1,
        backoff_factor=0,
    )

    async with AsyncFetcherClient(config) as client:
        response = await client.fetch(FetchRequest(url="https://example.com/retry"))

    assert response.status_code == 200
    assert response.attempts == 2
    assert route.call_count == 2


@pytest.mark.asyncio
@respx.mock
async def test_fetch_many_end_to_end() -> None:
    respx.get("https://example.com/first").mock(
        return_value=httpx.Response(200, content=b"first")
    )
    respx.get("https://example.com/second").mock(
        return_value=httpx.Response(201, content=b"second")
    )

    async with AsyncFetcherClient() as client:
        results = await client.fetch_many(
            [
                FetchRequest(url="https://example.com/first"),
                FetchRequest(url="https://example.com/second"),
            ]
        )

    assert len(results) == 2
    assert all(not isinstance(result, Exception) for result in results)

    first, second = results

    assert first.status_code == 200  # type: ignore[union-attr]
    assert first.body == b"first"  # type: ignore[union-attr]
    assert second.status_code == 201  # type: ignore[union-attr]
    assert second.body == b"second"  # type: ignore[union-attr]


@pytest.mark.asyncio
@respx.mock
async def test_fetch_many_isolates_request_failures() -> None:
    respx.get("https://example.com/good").mock(
        return_value=httpx.Response(200, content=b"ok")
    )
    respx.get("https://example.com/bad").mock(
        side_effect=httpx.ConnectError("Connection failed")
    )

    config = FetcherConfig(max_retries=0)

    async with AsyncFetcherClient(config) as client:
        results = await client.fetch_many(
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
async def test_retry_exhaustion_end_to_end() -> None:
    route = respx.get("https://example.com/unavailable").mock(
        return_value=httpx.Response(503)
    )

    config = FetcherConfig(
        raise_on_http_error=True,
        max_retries=1,
        backoff_factor=0,
    )

    async with AsyncFetcherClient(config) as client:
        with pytest.raises(RetryExhaustedError) as error:
            await client.fetch(FetchRequest(url="https://example.com/unavailable"))

    assert error.value.attempts == 2
    assert route.call_count == 2
