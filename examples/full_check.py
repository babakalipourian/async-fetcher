import asyncio
import json
import time

from pydantic import ValidationError

from async_fetcher import (
    AsyncFetcherClient,
    FetcherClosedError,
    FetcherConfig,
    FetchRequest,
    RetryExhaustedError,
)


def check_validation() -> None:
    print("\n=== 1. Configuration and Request Validation ===")

    try:
        FetcherConfig(max_concurrency=0)
    except ValidationError:
        print("PASS: Invalid configuration was rejected.")
    else:
        raise AssertionError("Expected ValidationError for max_concurrency=0.")

    try:
        FetchRequest(url="ftp://example.com")
    except ValidationError:
        print("PASS: Unsupported URL scheme was rejected.")
    else:
        raise AssertionError("Expected ValidationError for an unsupported URL scheme.")


async def check_single_fetch() -> None:
    print("\n=== 2. Single HTTP Request ===")

    config = FetcherConfig(timeout=10.0, max_retries=0)

    async with AsyncFetcherClient(config) as client:
        request = FetchRequest(
            url="https://httpbin.org/get",
            params={"source": "async-fetcher", "page": 1},
            headers={"X-Test-Client": "async-fetcher"},
        )

        response = await client.fetch(request)
        body = json.loads(response.body)

        assert response.status_code == 200
        assert body["args"]["source"] == "async-fetcher"
        assert body["args"]["page"] == "1"
        assert body["headers"]["X-Test-Client"] == "async-fetcher"

        print(f"PASS: HTTP {response.status_code}")
        print(f"URL: {response.url}")
        print(f"Elapsed: {response.elapsed_seconds:.3f}s")
        print(f"Attempts: {response.attempts}")
        print("PASS: Query parameters and custom headers were received.")


async def check_http_status_handling() -> None:
    print("\n=== 3. HTTP Error Handling ===")

    config = FetcherConfig(
        timeout=10.0,
        max_retries=0,
        raise_on_http_error=True,
    )

    requests = [
        FetchRequest(url="https://httpbin.org/get"),
        FetchRequest(url="https://httpbin.org/status/503"),
        FetchRequest(url="https://httpbin.org/get?check=third"),
    ]

    async with AsyncFetcherClient(config) as client:
        results = await client.fetch_many(requests)

    assert len(results) == 3
    assert not isinstance(results[0], Exception)
    assert isinstance(results[1], Exception)
    assert not isinstance(results[2], Exception)

    print("PASS: First request succeeded.")
    print(f"Middle request: {type(results[1]).__name__}")
    print("PASS: Third request succeeded despite the middle failure.")


async def check_retry() -> None:
    print("\n=== 4. Retry and Exhaustion ===")

    config = FetcherConfig(
        timeout=10.0,
        max_retries=2,
        backoff_factor=0.1,
        max_backoff=0.5,
        raise_on_http_error=True,
    )

    async with AsyncFetcherClient(config) as client:
        try:
            await client.fetch(FetchRequest(url="https://httpbin.org/status/503"))
        except RetryExhaustedError as exc:
            print(f"PASS: Retry exhaustion handled: {type(exc).__name__}")
        else:
            raise AssertionError("Expected RetryExhaustedError for HTTP 503.")


async def check_concurrency() -> None:
    print("\n=== 5. Bounded Concurrency ===")

    config = FetcherConfig(
        timeout=10.0,
        max_concurrency=2,
        max_connections=2,
        max_keepalive_connections=2,
        max_retries=0,
    )

    requests = [FetchRequest(url="https://httpbin.org/delay/1") for _ in range(4)]

    async with AsyncFetcherClient(config) as client:
        started = time.perf_counter()
        results = await client.fetch_many(requests)
        elapsed = time.perf_counter() - started

    successes = [
        result
        for result in results
        if not isinstance(result, Exception) and result.status_code == 200
    ]

    print(f"Successful requests: {len(successes)}/4")
    print(f"Total elapsed: {elapsed:.2f}s")
    print("Configured max_concurrency: 2")
    print("Note: Timing alone does not prove the concurrency limit.")


async def check_client_lifecycle() -> None:
    print("\n=== 6. Client Lifecycle ===")

    client = AsyncFetcherClient(FetcherConfig(max_retries=0))

    async with client:
        response = await client.fetch(FetchRequest(url="https://httpbin.org/get"))
        assert response.status_code == 200

    try:
        await client.fetch(FetchRequest(url="https://httpbin.org/get"))
    except FetcherClosedError:
        print("PASS: Requests after client closure are rejected.")
    else:
        raise AssertionError("Expected FetcherClosedError after closure.")


async def main() -> None:
    print("ASYNC-FETCHER INTEGRATION CHECK")
    print("=" * 40)

    check_validation()
    await check_single_fetch()
    await check_http_status_handling()
    await check_retry()
    await check_concurrency()
    await check_client_lifecycle()

    print("\n" + "=" * 40)
    print("ALL CHECKS COMPLETED")


if __name__ == "__main__":
    asyncio.run(main())
