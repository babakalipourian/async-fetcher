from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from async_fetcher import FetchResponse


def test_valid_response() -> None:
    response = FetchResponse(
        url="https://example.com/api",
        status_code=200,
        headers={"content-type": "application/json"},
        body=b'{"ok": true}',
        elapsed_seconds=0.25,
        attempts=1,
    )

    assert response.status_code == 200
    assert response.body == b'{"ok": true}'
    assert response.elapsed_seconds == 0.25
    assert response.attempts == 1
    assert response.fetched_at.tzinfo is not None


@pytest.mark.parametrize("status_code", [99, 600, 0, -1])
def test_invalid_status_code_is_rejected(status_code: int) -> None:
    with pytest.raises(ValidationError):
        FetchResponse(
            url="https://example.com",
            status_code=status_code,
            body=b"",
            elapsed_seconds=0.1,
            attempts=1,
        )


@pytest.mark.parametrize(
    "elapsed",
    [-1.0, float("nan"), float("inf"), -float("inf")],
)
def test_invalid_elapsed_seconds_is_rejected(elapsed: float) -> None:
    with pytest.raises(ValidationError):
        FetchResponse(
            url="https://example.com",
            status_code=200,
            body=b"",
            elapsed_seconds=elapsed,
            attempts=1,
        )


@pytest.mark.parametrize("attempts", [0, -1])
def test_invalid_attempt_count_is_rejected(attempts: int) -> None:
    with pytest.raises(ValidationError):
        FetchResponse(
            url="https://example.com",
            status_code=200,
            body=b"",
            elapsed_seconds=0.1,
            attempts=attempts,
        )


def test_naive_datetime_is_rejected() -> None:
    with pytest.raises(ValidationError):
        FetchResponse(
            url="https://example.com",
            status_code=200,
            body=b"",
            elapsed_seconds=0.1,
            attempts=1,
            fetched_at=datetime(2026, 1, 1),
        )


def test_datetime_is_normalized_to_utc() -> None:
    non_utc = timezone(timedelta(hours=3, minutes=30))
    timestamp = datetime(2026, 1, 1, 12, 0, tzinfo=non_utc)

    response = FetchResponse(
        url="https://example.com",
        status_code=200,
        body=b"",
        elapsed_seconds=0.1,
        attempts=1,
        fetched_at=timestamp,
    )

    assert response.fetched_at.utcoffset() == timedelta(0)
    assert response.fetched_at.hour == 8
    assert response.fetched_at.minute == 30


def test_response_headers_are_immutable() -> None:
    response = FetchResponse(
        url="https://example.com",
        status_code=200,
        headers={"content-type": "text/plain"},
        body=b"ok",
        elapsed_seconds=0.1,
        attempts=1,
    )

    with pytest.raises(TypeError):
        response.headers["content-type"] = "application/json"  # type: ignore[index]


def test_response_is_immutable() -> None:
    response = FetchResponse(
        url="https://example.com",
        status_code=200,
        body=b"ok",
        elapsed_seconds=0.1,
        attempts=1,
    )

    with pytest.raises(ValidationError):
        response.status_code = 201  # type: ignore[misc]


def test_unknown_response_fields_are_rejected() -> None:
    with pytest.raises(ValidationError):
        FetchResponse(
            url="https://example.com",
            status_code=200,
            body=b"",
            elapsed_seconds=0.1,
            attempts=1,
            unexpected="value",  # type: ignore[call-arg]
        )
