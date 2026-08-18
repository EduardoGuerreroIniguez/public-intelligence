import httpx2
import pytest

from public_intelligence.connectors.sercop import (
    SercopClient,
    SercopNotFoundError,
    SercopResponseError,
    SercopTransportError,
)


@pytest.mark.anyio
async def test_record_html_404_maps_to_not_found_without_body_in_message() -> None:
    body = b"<html>private diagnostic body</html>"

    async def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(
            404,
            headers={"content-type": "text/html"},
            content=body,
            request=request,
        )

    async with SercopClient(
        base_url="https://sercop.test",
        transport=httpx2.MockTransport(handler),
    ) as client:
        with pytest.raises(SercopNotFoundError) as captured:
            await client.get_record(ocid="ocds-missing")

    assert captured.value.status_code == 404
    assert captured.value.endpoint == "/api/record"
    assert "private diagnostic body" not in str(captured.value)


@pytest.mark.anyio
async def test_search_404_is_response_error_not_empty_results() -> None:
    async def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(
            404,
            headers={"content-type": "text/html"},
            content=b"Not Found",
            request=request,
        )

    async with SercopClient(
        base_url="https://sercop.test",
        transport=httpx2.MockTransport(handler),
    ) as client:
        with pytest.raises(SercopResponseError) as captured:
            await client.search(year=2026, search="agua")

    assert captured.value.status_code == 404
    assert not isinstance(captured.value, SercopNotFoundError)


@pytest.mark.anyio
@pytest.mark.parametrize("status_code", [429, 500, 503])
async def test_unexpected_status_maps_to_response_error(status_code: int) -> None:
    async def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(status_code, content=b"failure", request=request)

    async with SercopClient(
        base_url="https://sercop.test",
        transport=httpx2.MockTransport(handler),
    ) as client:
        with pytest.raises(SercopResponseError) as captured:
            await client.search(year=2026, search="agua")

    assert captured.value.status_code == status_code


@pytest.mark.anyio
async def test_malformed_json_maps_to_response_error() -> None:
    async def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(
            200,
            headers={"content-type": "application/json"},
            content=b"{not-json",
            request=request,
        )

    async with SercopClient(
        base_url="https://sercop.test",
        transport=httpx2.MockTransport(handler),
    ) as client:
        with pytest.raises(SercopResponseError, match="malformed JSON"):
            await client.search(year=2026, search="agua")


@pytest.mark.anyio
async def test_unexpected_successful_content_type_maps_to_response_error() -> None:
    async def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(
            200,
            headers={"content-type": "text/html"},
            content=b"<html>not json</html>",
            request=request,
        )

    async with SercopClient(
        base_url="https://sercop.test",
        transport=httpx2.MockTransport(handler),
    ) as client:
        with pytest.raises(SercopResponseError, match="content type"):
            await client.search(year=2026, search="agua")


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("operation", "body"),
    [
        ("search", b'{"data":[]}'),
        ("record", b'{"version":"1.1","releases":[]}'),
    ],
)
async def test_invalid_envelope_maps_to_response_error(
    operation: str,
    body: bytes,
) -> None:
    async def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(
            200,
            headers={"content-type": "application/json"},
            content=body,
            request=request,
        )

    async with SercopClient(
        base_url="https://sercop.test",
        transport=httpx2.MockTransport(handler),
    ) as client:
        with pytest.raises(SercopResponseError, match="invalid source envelope"):
            if operation == "search":
                await client.search(year=2026, search="agua")
            else:
                await client.get_record(ocid="ocds-invalid")


@pytest.mark.anyio
async def test_transport_failure_is_wrapped() -> None:
    async def handler(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.ConnectError("connection failed", request=request)

    async with SercopClient(
        base_url="https://sercop.test",
        transport=httpx2.MockTransport(handler),
    ) as client:
        with pytest.raises(SercopTransportError) as captured:
            await client.search(year=2026, search="agua")

    assert captured.value.endpoint == "/api/search_ocds"
    assert isinstance(captured.value.__cause__, httpx2.ConnectError)
