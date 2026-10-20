import httpx
import pytest
import respx

from async_fetcher.exceptions import TransportError
from async_fetcher.models.request import FetchRequest
from async_fetcher.transport.http import HTTPTransport


@pytest.fixture
def transport() -> HTTPTransport:
    return HTTPTransport(
        timeout=5.0,
        max_connections=5,
        max_keepalive_connections=2,
    )


@pytest.mark.asyncio
@respx.mock
async def test_send_returns_valid_response(
    transport: HTTPTransport,
) -> None:
    respx.get("https://example.com/api").mock(
        return_value=httpx.Response(
            200,
            json={"ok": True},
        )
    )

    try:
        response = await transport.send(FetchRequest(url="https://example.com/api"))

        assert response.status_code == 200
        assert response.attempts == 1
        assert b'"ok":true' in response.body
        assert response.elapsed_seconds >= 0
    finally:
        await transport.aclose()


@pytest.mark.asyncio
@respx.mock
async def test_send_preserves_response_headers(
    transport: HTTPTransport,
) -> None:
    respx.get("https://example.com/api").mock(
        return_value=httpx.Response(
            200,
            headers={"X-Test": "value"},
            content=b"hello",
        )
    )

    try:
        response = await transport.send(FetchRequest(url="https://example.com/api"))

        assert response.headers["x-test"] == "value"
        assert response.body == b"hello"
    finally:
        await transport.aclose()


@pytest.mark.asyncio
@respx.mock
async def test_send_passes_method_headers_and_params(
    transport: HTTPTransport,
) -> None:
    route = respx.post("https://example.com/api").mock(
        return_value=httpx.Response(201, content=b"created")
    )

    try:
        response = await transport.send(
            FetchRequest(
                url="https://example.com/api",
                method="POST",
                headers={"X-Test": "value"},
                params={"page": 2},
            )
        )

        assert response.status_code == 201
        assert route.called
        assert route.calls.last.request.headers["X-Test"] == "value"
        assert "page=2" in str(route.calls.last.request.url)
    finally:
        await transport.aclose()


@pytest.mark.asyncio
@respx.mock
async def test_timeout_is_converted_to_transport_error(
    transport: HTTPTransport,
) -> None:
    respx.get("https://example.com/slow").mock(
        side_effect=httpx.ReadTimeout("Request timed out")
    )

    try:
        with pytest.raises(TransportError, match="timed out"):
            await transport.send(FetchRequest(url="https://example.com/slow"))
    finally:
        await transport.aclose()


@pytest.mark.asyncio
@respx.mock
async def test_request_error_is_converted_to_transport_error(
    transport: HTTPTransport,
) -> None:
    respx.get("https://example.com/fail").mock(
        side_effect=httpx.ConnectError("Connection failed")
    )

    try:
        with pytest.raises(TransportError, match="failed"):
            await transport.send(FetchRequest(url="https://example.com/fail"))
    finally:
        await transport.aclose()


@pytest.mark.asyncio
@respx.mock
async def test_closed_transport_rejects_requests(
    transport: HTTPTransport,
) -> None:
    await transport.aclose()

    with pytest.raises(RuntimeError, match="closed"):
        await transport.send(FetchRequest(url="https://example.com"))


@pytest.mark.asyncio
async def test_close_is_idempotent(transport: HTTPTransport) -> None:
    await transport.aclose()
    await transport.aclose()


@pytest.mark.asyncio
@respx.mock
async def test_transport_context_manager() -> None:
    respx.get("https://example.com").mock(
        return_value=httpx.Response(200, content=b"ok")
    )

    async with HTTPTransport(
        timeout=5,
        max_connections=2,
        max_keepalive_connections=1,
    ) as transport:
        response = await transport.send(FetchRequest(url="https://example.com"))
        assert response.status_code == 200
