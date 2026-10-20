import httpx
import pytest
import respx

from async_fetcher import (
    AsyncFetcherClient,
    FetcherClosedError,
    FetcherConfig,
    FetchRequest,
)


@pytest.mark.asyncio
@respx.mock
async def test_client_fetch() -> None:
    respx.get("https://example.com/api").mock(
        return_value=httpx.Response(200, content=b"hello")
    )

    async with AsyncFetcherClient() as client:
        response = await client.fetch(FetchRequest(url="https://example.com/api"))

    assert response.status_code == 200
    assert response.body == b"hello"


@pytest.mark.asyncio
@respx.mock
async def test_client_fetch_many() -> None:
    respx.get("https://example.com/one").mock(
        return_value=httpx.Response(200, content=b"one")
    )
    respx.get("https://example.com/two").mock(
        return_value=httpx.Response(200, content=b"two")
    )

    async with AsyncFetcherClient() as client:
        results = await client.fetch_many(
            [
                FetchRequest(url="https://example.com/one"),
                FetchRequest(url="https://example.com/two"),
            ]
        )

    assert len(results) == 2
    assert all(not isinstance(item, Exception) for item in results)


@pytest.mark.asyncio
async def test_client_accepts_custom_config() -> None:
    config = FetcherConfig(max_concurrency=5)
    client = AsyncFetcherClient(config)

    assert client is not None

    await client.aclose()


@pytest.mark.asyncio
async def test_client_rejects_fetch_after_close() -> None:
    client = AsyncFetcherClient()
    await client.aclose()

    with pytest.raises(FetcherClosedError):
        await client.fetch(FetchRequest(url="https://example.com"))


@pytest.mark.asyncio
async def test_client_close_is_idempotent() -> None:
    client = AsyncFetcherClient()

    await client.aclose()
    await client.aclose()


@pytest.mark.asyncio
async def test_client_context_manager_closes_client() -> None:
    client = AsyncFetcherClient()

    async with client:
        pass

    with pytest.raises(FetcherClosedError):
        await client.fetch(FetchRequest(url="https://example.com"))
