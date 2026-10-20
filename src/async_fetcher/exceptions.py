class AsyncFetcherError(Exception):
    """Base exception for all async-fetcher errors."""


class ConfigurationError(AsyncFetcherError):
    """Raised when the fetcher configuration is invalid."""


class RequestError(AsyncFetcherError):
    """Raised when an HTTP request fails."""

    def __init__(
        self,
        message: str,
        *,
        url: str,
        method: str,
    ) -> None:
        super().__init__(message)
        self.url = url
        self.method = method


class RetryExhaustedError(RequestError):
    """Raised when all retry attempts have been exhausted."""

    def __init__(
        self,
        message: str,
        *,
        url: str,
        method: str,
        attempts: int,
        last_exception: Exception | None = None,
    ) -> None:
        super().__init__(message, url=url, method=method)
        self.attempts = attempts
        self.last_exception = last_exception


class HTTPStatusError(RequestError):
    """Raised when an HTTP response has an unsuccessful status code."""

    def __init__(
        self,
        message: str,
        *,
        url: str,
        method: str,
        status_code: int,
        response_body: bytes = b"",
    ) -> None:
        super().__init__(message, url=url, method=method)
        self.status_code = status_code
        self.response_body = response_body


class ResponseValidationError(AsyncFetcherError):
    """Raised when an HTTP response cannot be validated."""


class TransportError(RequestError):
    """Raised when the HTTP transport encounters an error."""


class FetcherClosedError(AsyncFetcherError):
    """Raised when attempting to use a closed fetcher."""


class ConcurrencyLimitError(AsyncFetcherError):
    """Raised when concurrency configuration is invalid."""


class RetryPolicyError(AsyncFetcherError):
    """Raised when retry configuration is invalid."""
