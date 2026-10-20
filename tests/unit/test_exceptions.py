import pytest

from async_fetcher.exceptions import (
    AsyncFetcherError,
    ConcurrencyLimitError,
    FetcherClosedError,
    HTTPStatusError,
    RequestError,
    ResponseValidationError,
    RetryExhaustedError,
    RetryPolicyError,
    TransportError,
)


def test_base_exception() -> None:
    error = AsyncFetcherError("failure")

    assert str(error) == "failure"
    assert isinstance(error, Exception)


def test_request_error_stores_request_details() -> None:
    error = RequestError(
        "Request failed",
        url="https://example.com",
        method="GET",
    )

    assert error.url == "https://example.com"
    assert error.method == "GET"
    assert str(error) == "Request failed"


def test_transport_error_inherits_request_error() -> None:
    error = TransportError(
        "Connection failed",
        url="https://example.com",
        method="GET",
    )

    assert isinstance(error, RequestError)
    assert error.url == "https://example.com"


def test_http_status_error_stores_response_details() -> None:
    error = HTTPStatusError(
        "HTTP error",
        url="https://example.com",
        method="GET",
        status_code=503,
        response_body=b"unavailable",
    )

    assert error.status_code == 503
    assert error.response_body == b"unavailable"
    assert error.url == "https://example.com"
    assert error.method == "GET"


def test_retry_exhausted_error_stores_attempts() -> None:
    original_error = ConnectionError("Connection lost")

    error = RetryExhaustedError(
        "Retries exhausted",
        url="https://example.com",
        method="GET",
        attempts=4,
        last_exception=original_error,
    )

    assert error.attempts == 4
    assert error.last_exception is original_error
    assert error.url == "https://example.com"


@pytest.mark.parametrize(
    "error",
    [
        FetcherClosedError("closed"),
        ResponseValidationError("invalid response"),
        ConcurrencyLimitError("invalid concurrency"),
        RetryPolicyError("invalid retry policy"),
    ],
)
def test_specialized_errors_inherit_base(error: Exception) -> None:
    assert isinstance(error, AsyncFetcherError)
