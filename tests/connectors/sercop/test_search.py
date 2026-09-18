import json
from datetime import timedelta
from hashlib import sha256

import httpx2
import pytest

from public_intelligence.connectors.sercop import (
    SercopClient,
    SercopResponseError,
)


@pytest.mark.anyio
async def test_search_preserves_fixture_contract_and_provenance(
    search_body: bytes,
) -> None:
    requests: list[httpx2.Request] = []

    async def handler(request: httpx2.Request) -> httpx2.Response:
        requests.append(request)
        return httpx2.Response(
            200,
            headers={
                "content-type": "application/json; charset=utf-8",
                "etag": '"fixture-etag"',
                "last-modified": "Mon, 17 Aug 2026 19:31:16 GMT",
            },
            content=search_body,
            request=request,
        )

    async with SercopClient(
        base_url="https://sercop.test",
        transport=httpx2.MockTransport(handler),
    ) as client:
        result = await client.search(year=2015, search="agua")

    assert len(requests) == 1
    request = requests[0]
    assert request.method == "GET"
    assert request.url.path == "/api/search_ocds"
    assert dict(request.url.params) == {
        "year": "2015",
        "search": "agua",
        "page": "1",
    }
    assert request.headers["user-agent"] == "public-intelligence"

    assert result.raw_body == search_body
    assert result.provenance.payload_sha256 == sha256(search_body).hexdigest()
    assert result.provenance.payload_size == len(search_body)
    assert result.provenance.source_key == "sercop"
    assert result.provenance.access_mechanism == "keyword_search"
    assert result.provenance.endpoint == "/api/search_ocds"
    assert dict(result.provenance.request_parameters) == {
        "year": 2015,
        "search": "agua",
        "page": 1,
    }
    assert result.provenance.http_status == 200
    assert result.provenance.content_type == "application/json; charset=utf-8"
    assert result.provenance.etag == '"fixture-etag"'
    assert result.provenance.last_modified == "Mon, 17 Aug 2026 19:31:16 GMT"
    assert result.provenance.retrieved_at.utcoffset() == timedelta(0)

    assert result.data.total == 3515
    assert result.data.page == 1
    assert result.data.pages == 352
    assert result.data.has_next is True
    summary = result.data.data[0]
    assert type(summary.id) is int
    assert type(summary.year) is int
    assert type(summary.month) is int
    assert summary.id == 1290034
    assert summary.ocid == "ocds-5wno2w-CE-20150000092768-23237"
    assert summary.id != summary.ocid
    assert summary.amount == "24.200000"
    assert summary.budget == "24.2"
    assert summary.buyer.startswith("DIRECCION DISTRITAL")
    assert summary.suppliers == (
        "LABORATORIOS INDUSTRIALES FARMACEUTICOS ECUATORIANOS LIFE C.A."
    )


@pytest.mark.anyio
async def test_search_sends_explicit_page_and_optional_filters(
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

    async with SercopClient(
        base_url="https://sercop.test",
        transport=httpx2.MockTransport(handler),
    ) as client:
        result = await client.search(
            year=2026,
            search="agua",
            page=2,
            buyer="municipio",
            supplier="proveedor",
        )

    assert dict(requests[0].url.params) == {
        "year": "2026",
        "search": "agua",
        "page": "2",
        "buyer": "municipio",
        "supplier": "proveedor",
    }
    assert dict(result.provenance.request_parameters) == {
        "year": 2026,
        "search": "agua",
        "page": 2,
        "buyer": "municipio",
        "supplier": "proveedor",
    }


@pytest.mark.anyio
async def test_search_tolerates_documented_nulls_and_additive_fields(
    search_body: bytes,
) -> None:
    payload = json.loads(search_body)
    payload["futureEnvelopeField"] = {"value": True}
    first_summary = payload["data"][0]
    for field in (
        "method",
        "internal_type",
        "suppliers",
        "amount",
        "title",
        "description",
        "budget",
        "locality",
        "region",
    ):
        first_summary[field] = None
    first_summary["futureSummaryField"] = "preserved"
    body = json.dumps(payload).encode()

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
        result = await client.search(year=2015, search="agua")

    summary = result.data.data[0]
    assert summary.amount is None
    assert summary.suppliers is None
    assert summary.model_extra == {"futureSummaryField": "preserved"}
    assert result.data.model_extra == {"futureEnvelopeField": {"value": True}}
    assert summary.locality is None
    assert summary.region is None


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("id", "1290034"),
        ("year", "2015"),
        ("month", "1"),
        ("amount", 24.2),
        ("budget", 24.2),
    ],
)
async def test_search_rejects_unsafe_type_coercion(
    search_body: bytes,
    field: str,
    value: object,
) -> None:
    payload = json.loads(search_body)
    payload["data"][0][field] = value
    body = json.dumps(payload).encode()

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
        with pytest.raises(SercopResponseError):
            await client.search(year=2015, search="agua")
