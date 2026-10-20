import pytest
from pydantic import ValidationError

from async_fetcher import FetchRequest


def test_valid_request_uses_default_method() -> None:
    request = FetchRequest(url="https://example.com/api")

    assert str(request.url) == "https://example.com/api"
    assert request.method == "GET"
    assert request.timeout is None
    assert dict(request.headers) == {}
    assert dict(request.params) == {}


def test_method_is_normalized() -> None:
    request = FetchRequest(
        url="https://example.com",
        method="  post  ",
    )

    assert request.method == "POST"


@pytest.mark.parametrize("method", ["", "   ", "GET POST", "GE\nT"])
def test_invalid_method_is_rejected(method: str) -> None:
    with pytest.raises(ValidationError):
        FetchRequest(url="https://example.com", method=method)


@pytest.mark.parametrize(
    "url",
    [
        "ftp://example.com/file",
        "file:///tmp/example.txt",
        "not-a-url",
    ],
)
def test_invalid_url_is_rejected(url: str) -> None:
    with pytest.raises(ValidationError):
        FetchRequest(url=url)


def test_invalid_header_name_is_rejected() -> None:
    with pytest.raises(ValidationError):
        FetchRequest(
            url="https://example.com",
            headers={"Bad Header": "value"},
        )


@pytest.mark.parametrize("value", ["hello\r\nInjected: true", "bad\nvalue"])
def test_header_newlines_are_rejected(value: str) -> None:
    with pytest.raises(ValidationError):
        FetchRequest(
            url="https://example.com",
            headers={"X-Test": value},
        )


def test_empty_header_name_is_rejected() -> None:
    with pytest.raises(ValidationError):
        FetchRequest(
            url="https://example.com",
            headers={"": "value"},
        )


def test_valid_headers_and_params_are_preserved() -> None:
    request = FetchRequest(
        url="https://example.com",
        headers={"Accept": "application/json"},
        params={"page": 2, "active": True},
    )

    assert request.headers["Accept"] == "application/json"
    assert request.params["page"] == 2
    assert request.params["active"] is True


def test_headers_are_immutable() -> None:
    request = FetchRequest(
        url="https://example.com",
        headers={"Accept": "application/json"},
    )

    with pytest.raises(TypeError):
        request.headers["Accept"] = "text/plain"  # type: ignore[index]


def test_params_are_immutable() -> None:
    request = FetchRequest(
        url="https://example.com",
        params={"page": 1},
    )

    with pytest.raises(TypeError):
        request.params["page"] = 2  # type: ignore[index]


@pytest.mark.parametrize("timeout", [0, -1])
def test_invalid_request_timeout_is_rejected(timeout: float) -> None:
    with pytest.raises(ValidationError):
        FetchRequest(
            url="https://example.com",
            timeout=timeout,
        )


def test_unknown_fields_are_rejected() -> None:
    with pytest.raises(ValidationError):
        FetchRequest(
            url="https://example.com",
            retries=3,  # type: ignore[call-arg]
        )
