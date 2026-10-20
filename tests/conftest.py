import pytest

from async_fetcher import FetcherConfig, FetchRequest


@pytest.fixture
def default_config() -> FetcherConfig:
    """Provide the default fetcher configuration."""
    return FetcherConfig()


@pytest.fixture
def valid_request() -> FetchRequest:
    """Provide a valid HTTP request for tests."""
    return FetchRequest(url="https://example.com/api")


@pytest.fixture
def custom_config() -> FetcherConfig:
    """Provide a configuration suitable for testing retries and concurrency."""
    return FetcherConfig(
        timeout=5.0,
        max_concurrency=3,
        max_connections=3,
        max_keepalive_connections=2,
        max_retries=2,
        backoff_factor=0.1,
        max_backoff=1.0,
    )
