from collections.abc import Callable, Coroutine

import httpx2
import pytest

from public_intelligence.connectors.sercop import SercopClient

AsyncHandler = Callable[[httpx2.Request], Coroutine[None, None, httpx2.Response]]


class TrackingMockTransport(httpx2.MockTransport):
    def __init__(self, handler: AsyncHandler) -> None:
        super().__init__(handler)
        self.close_count = 0

    async def aclose(self) -> None:
        self.close_count += 1
        await super().aclose()


@pytest.mark.anyio
async def test_client_reuses_transport_and_context_manager_closes_it(
    search_body: bytes,
) -> None:
    request_count = 0

    async def handler(request: httpx2.Request) -> httpx2.Response:
        nonlocal request_count
        request_count += 1
        return httpx2.Response(
            200,
            headers={"content-type": "application/json"},
            content=search_body,
            request=request,
        )

    transport = TrackingMockTransport(handler)
    async with SercopClient(
        base_url="https://sercop.test/",
        transport=transport,
    ) as client:
        await client.search(year=2015, search="agua")
        await client.search(year=2015, search="agua", page=2)
        assert transport.close_count == 0

    assert request_count == 2
    assert transport.close_count == 1


@pytest.mark.anyio
async def test_explicit_close_is_idempotent() -> None:
    async def handler(request: httpx2.Request) -> httpx2.Response:
        raise AssertionError("no request expected")

    transport = TrackingMockTransport(handler)
    client = SercopClient(base_url="https://sercop.test", transport=transport)

    await client.aclose()
    await client.aclose()

    assert transport.close_count == 1


@pytest.mark.anyio
async def test_default_base_url_targets_official_public_platform(
    search_body: bytes,
) -> None:
    requests: list[httpx2.Request] = []

    async def handler(request: httpx2.Request) -> httpx2.Response:
        requests.append(request)
        return httpx2.Response(
            200,
            headers={"content-type": "application/json"},
            content=search_body,
            request=request,
        )

    async with SercopClient(transport=httpx2.MockTransport(handler)) as client:
        await client.search(year=2015, search="agua")

    assert requests[0].url.host == "datosabiertos.compraspublicas.gob.ec"
    assert requests[0].url.path == "/PLATAFORMA/api/search_ocds"


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("arguments", "error_type"),
    [
        ({"year": True, "search": "agua"}, TypeError),
        ({"year": "2026", "search": "agua"}, TypeError),
        ({"year": 2026, "search": "  "}, ValueError),
        ({"year": 2026, "search": "ab"}, ValueError),
        ({"year": 2026, "search": "agua", "page": 0}, ValueError),
        ({"year": 2026, "search": "agua", "page": True}, TypeError),
        ({"year": 2026, "search": "agua", "buyer": 1}, TypeError),
    ],
)
async def test_search_rejects_invalid_caller_input(
    arguments: dict[str, object],
    error_type: type[Exception],
) -> None:
    async def handler(request: httpx2.Request) -> httpx2.Response:
        raise AssertionError("request should not be sent")

    async with SercopClient(
        base_url="https://sercop.test",
        transport=httpx2.MockTransport(handler),
    ) as client:
        with pytest.raises(error_type):
            await client.search(**arguments)  # type: ignore[arg-type]


@pytest.mark.anyio
@pytest.mark.parametrize("ocid", ["", "   "])
async def test_record_rejects_blank_ocid(ocid: str) -> None:
    async def handler(request: httpx2.Request) -> httpx2.Response:
        raise AssertionError("request should not be sent")

    async with SercopClient(
        base_url="https://sercop.test",
        transport=httpx2.MockTransport(handler),
    ) as client:
        with pytest.raises(ValueError, match="must not be blank"):
            await client.get_record(ocid=ocid)
