# async-fetcher

A typed Python library for asynchronous HTTP requests with bounded concurrency, retry handling, configurable timeouts, and structured logging.

## Features

- Asynchronous HTTP requests powered by HTTPX.
- Bounded concurrency to control simultaneous requests.
- Configurable timeouts and connection limits.
- Retry handling with exponential backoff and jitter.
- Configurable retryable HTTP status codes.
- Batch requests with result ordering preserved.
- Per-request error isolation when using `fetch_many`.
- Pydantic-based configuration and data models.
- Structured logging with `structlog`.
- Type information distributed through `py.typed`.
- Automated tests, linting, formatting, and CI.

## Requirements

- Python 3.11 or newer.

## Installation

Install the package from a local checkout:

```bash
python -m pip install .
```

For development, including testing and code-quality tools:

```bash
python -m pip install -e ".[dev]"
```

## Quick Start

```python
import asyncio

from async_fetcher import (
    AsyncFetcherClient,
    FetcherConfig,
    FetchRequest,
)


async def main() -> None:
    config = FetcherConfig(
        timeout=10.0,
        max_concurrency=5,
        max_retries=2,
    )

    requests = [
        FetchRequest(url="https://httpbin.org/get"),
        FetchRequest(
            url="https://httpbin.org/get",
            params={"source": "async-fetcher"},
        ),
    ]

    async with AsyncFetcherClient(config) as client:
        results = await client.fetch_many(requests)

    for result in results:
        if isinstance(result, Exception):
            print(f"Request failed: {result}")
            continue

        print(f"Status: {result.status_code}")
        print(f"URL: {result.url}")
        print(f"Attempts: {result.attempts}")
        print(f"Elapsed: {result.elapsed_seconds:.3f}s")


if __name__ == "__main__":
    asyncio.run(main())
```

The example uses `httpbin.org`, so an internet connection is required to run it.

## Configuration

Configure the client with `FetcherConfig`:

```python
from async_fetcher import FetcherConfig

config = FetcherConfig(
    timeout=10.0,
    max_concurrency=20,
    max_connections=20,
    max_keepalive_connections=10,
    max_retries=3,
    backoff_factor=0.5,
    max_backoff=30.0,
    follow_redirects=True,
    raise_on_http_error=False,
)
```

These values illustrate the available configuration options and their defaults. You can override them to suit your workload.

- `timeout`: Request timeout in seconds.
- `max_concurrency`: Maximum number of concurrently processed requests.
- `max_connections`: Maximum number of HTTP connections.
- `max_keepalive_connections`: Maximum number of reusable keep-alive connections.
- `max_retries`: Configured retry count.
- `backoff_factor`: Base factor used for retry backoff.
- `max_backoff`: Maximum backoff delay in seconds.
- `follow_redirects`: Whether HTTP redirects are followed.
- `raise_on_http_error`: Whether HTTP error responses should raise an exception.

## Batch Requests and Error Handling

`fetch_many()` preserves the input order of results and isolates failures on a per-request basis. A failed request can return an exception in its result position without preventing other requests from completing.

Check each result before accessing response attributes:

```python
results = await client.fetch_many(requests)

for result in results:
    if isinstance(result, Exception):
        print(f"Failed: {result}")
    else:
        print(result.status_code)
```

The package exposes exceptions including `RequestError`, `TransportError`, `HTTPStatusError`, `RetryExhaustedError`, and `FetcherClosedError`.

## Development

Install development dependencies:

```bash
python -m pip install -e ".[dev]"
```

Run the test suite with coverage:

```bash
python -m pytest
```

Run Ruff lint checks:

```bash
ruff check src tests
```

Format the code:

```bash
ruff format src tests
```

Run static type checking:

```bash
mypy src
```

Run all configured pre-commit hooks:

```bash
pre-commit run --all-files
```

## Continuous Integration

GitHub Actions runs the test suite and Ruff checks on Python 3.11, 3.12, and 3.13 for pushes and pull requests.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
