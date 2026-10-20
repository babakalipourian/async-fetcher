import asyncio

from async_fetcher import (
    AsyncFetcherClient,
    FetcherConfig,
    FetchRequest,
)


async def main() -> None:
    config = FetcherConfig(
        timeout=10.0,
        max_concurrency=3,
        max_retries=2,
    )

    requests = [
        FetchRequest(url="https://httpbin.org/get"),
        FetchRequest(
            url="https://httpbin.org/get",
            params={"source": "async-fetcher", "page": 1},
        ),
        FetchRequest(url="https://httpbin.org/status/404"),
    ]

    async with AsyncFetcherClient(config) as client:
        results = await client.fetch_many(requests)

    for index, result in enumerate(results, start=1):
        print(f"\n--- Request {index} ---")

        if isinstance(result, Exception):
            print(f"Error: {type(result).__name__}: {result}")
            continue

        print(f"URL: {result.url}")
        print(f"Status: {result.status_code}")
        print(f"Elapsed: {result.elapsed_seconds:.3f}s")
        print(f"Attempts: {result.attempts}")
        print(f"Body preview: {result.body[:200].decode('utf-8', errors='replace')}")


if __name__ == "__main__":
    asyncio.run(main())
