import asyncio

import pytest

from async_fetcher import FetcherConfig
from async_fetcher.services.retry import RetryPolicy


@pytest.fixture
def retry_policy() -> RetryPolicy:
    return RetryPolicy(
        FetcherConfig(
            max_retries=3,
            backoff_factor=0,
            max_backoff=1,
        )
    )


@pytest.mark.asyncio
async def test_success_on_first_attempt(
    retry_policy: RetryPolicy,
) -> None:
    async def operation() -> str:
        return "success"

    result = await retry_policy.execute(
        operation,
        should_retry=lambda exc: True,
    )

    assert result == "success"


@pytest.mark.asyncio
async def test_retries_then_succeeds(
    retry_policy: RetryPolicy,
) -> None:
    attempts = 0

    async def operation() -> str:
        nonlocal attempts
        attempts += 1

        if attempts < 3:
            raise ConnectionError("temporary failure")

        return "success"

    result = await retry_policy.execute(
        operation,
        should_retry=lambda exc: isinstance(exc, ConnectionError),
    )

    assert result == "success"
    assert attempts == 3


@pytest.mark.asyncio
async def test_exhausted_retries_raise_last_exception(
    retry_policy: RetryPolicy,
) -> None:
    attempts = 0

    async def operation() -> str:
        nonlocal attempts
        attempts += 1
        raise ConnectionError("connection failed")

    with pytest.raises(ConnectionError, match="connection failed"):
        await retry_policy.execute(
            operation,
            should_retry=lambda exc: isinstance(exc, ConnectionError),
        )

    assert attempts == 4


@pytest.mark.asyncio
async def test_non_retryable_error_is_raised_immediately(
    retry_policy: RetryPolicy,
) -> None:
    attempts = 0

    async def operation() -> str:
        nonlocal attempts
        attempts += 1
        raise ValueError("invalid input")

    with pytest.raises(ValueError, match="invalid input"):
        await retry_policy.execute(
            operation,
            should_retry=lambda exc: isinstance(exc, ConnectionError),
        )

    assert attempts == 1


@pytest.mark.asyncio
async def test_zero_retries_runs_operation_once() -> None:
    policy = RetryPolicy(FetcherConfig(max_retries=0))
    attempts = 0

    async def operation() -> str:
        nonlocal attempts
        attempts += 1
        raise ConnectionError("failed")

    with pytest.raises(ConnectionError):
        await policy.execute(
            operation,
            should_retry=lambda exc: True,
        )

    assert attempts == 1


@pytest.mark.asyncio
async def test_retry_backoff_is_capped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    policy = RetryPolicy(
        FetcherConfig(
            max_retries=2,
            backoff_factor=10,
            max_backoff=0.01,
        )
    )
    delays: list[float] = []

    async def fake_sleep(delay: float) -> None:
        delays.append(delay)

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    attempts = 0

    async def operation() -> str:
        nonlocal attempts
        attempts += 1

        if attempts < 3:
            raise ConnectionError("temporary failure")

        return "success"

    result = await policy.execute(
        operation,
        should_retry=lambda exc: isinstance(exc, ConnectionError),
    )

    assert result == "success"
    assert attempts == 3
    assert len(delays) == 2
    assert all(0 <= delay <= 0.01 for delay in delays)


@pytest.mark.asyncio
async def test_cancellation_is_not_retried(
    retry_policy: RetryPolicy,
) -> None:
    attempts = 0

    async def operation() -> str:
        nonlocal attempts
        attempts += 1
        raise asyncio.CancelledError

    with pytest.raises(asyncio.CancelledError):
        await retry_policy.execute(
            operation,
            should_retry=lambda exc: True,
        )

    assert attempts == 1
