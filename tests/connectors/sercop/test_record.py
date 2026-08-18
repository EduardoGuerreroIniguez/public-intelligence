import json
from hashlib import sha256

import httpx2
import pytest

from public_intelligence.connectors.sercop import SercopClient, SercopResponseError


@pytest.mark.anyio
@pytest.mark.parametrize(
    "fixture_name",
    [
        "record-2015-ocds-5wno2w-CE-20150000092768-23237.json",
        "record-2026-ocds-5wno2w-CE-20260002969199-2455.json",
        "record-2026-ocds-5wno2w-RE-OACL-GADMSFD-2026-001-2452.json",
    ],
)
async def test_record_parses_captured_fixture_and_preserves_evidence(
    fixture_name: str,
    record_bodies: dict[str, bytes],
) -> None:
    body = record_bodies[fixture_name]
    source = json.loads(body)
    requests: list[httpx2.Request] = []

    async def handler(request: httpx2.Request) -> httpx2.Response:
        requests.append(request)
        return httpx2.Response(
            200,
            headers={"content-type": "application/json"},
            content=body,
            request=request,
        )

    ocid = source["releases"][0]["ocid"]
    async with SercopClient(
        base_url="https://sercop.test",
        transport=httpx2.MockTransport(handler),
    ) as client:
        result = await client.get_record(ocid=ocid)

    assert requests[0].url.path == "/api/record"
    assert dict(requests[0].url.params) == {"ocid": ocid}
    assert result.raw_body == body
    assert result.provenance.payload_sha256 == sha256(body).hexdigest()
    assert result.provenance.payload_size == len(body)
    assert result.provenance.access_mechanism == "ocid_record"
    assert dict(result.provenance.request_parameters) == {"ocid": ocid}

    assert result.data.version == "1.1"
    assert result.data.license == "https://creativecommons.org/licenses/by/3.0/ec/"
    assert len(result.data.releases) == 1
    release = result.data.releases[0]
    assert release.ocid == ocid
    assert release.id == source["releases"][0]["id"]
    assert release.tag == source["releases"][0]["tag"]
    assert release.buyer is not None
    assert release.tender is not None
    assert release.awards is not None
    assert release.parties is not None
    assert release.parties[0].model_extra is not None
    assert release.awards[0].model_extra is not None
    assert "address" in release.parties[0].model_extra
    assert "items" in release.awards[0].model_extra


@pytest.mark.anyio
async def test_record_supports_sparse_observed_lifecycle_sections(
    record_bodies: dict[str, bytes],
) -> None:
    fixture_name = "record-2026-ocds-5wno2w-RE-OACL-GADMSFD-2026-001-2452.json"
    body = record_bodies[fixture_name]
    ocid = json.loads(body)["releases"][0]["ocid"]

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
        result = await client.get_record(ocid=ocid)

    release = result.data.releases[0]
    assert release.contracts is None
    assert release.related_processes is None
    assert release.awards is not None
    assert release.awards[0].status is None


@pytest.mark.anyio
async def test_record_tolerates_additive_fields_at_typed_levels(
    record_bodies: dict[str, bytes],
) -> None:
    body = next(iter(record_bodies.values()))
    payload = json.loads(body)
    payload["futurePackageField"] = True
    release = payload["releases"][0]
    release["futureReleaseField"] = {"value": 1}
    release["tender"]["futureTenderField"] = "preserved"
    modified_body = json.dumps(payload).encode()
    ocid = release["ocid"]

    async def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(
            200,
            headers={"content-type": "application/json"},
            content=modified_body,
            request=request,
        )

    async with SercopClient(
        base_url="https://sercop.test",
        transport=httpx2.MockTransport(handler),
    ) as client:
        result = await client.get_record(ocid=ocid)

    parsed_release = result.data.releases[0]
    assert result.data.model_extra == {"futurePackageField": True}
    assert parsed_release.model_extra == {"futureReleaseField": {"value": 1}}
    assert parsed_release.tender is not None
    assert parsed_release.tender.model_extra == {"futureTenderField": "preserved"}


@pytest.mark.anyio
async def test_record_rejects_string_coercion_for_numeric_money(
    record_bodies: dict[str, bytes],
) -> None:
    body = next(iter(record_bodies.values()))
    payload = json.loads(body)
    release = payload["releases"][0]
    release["awards"][0]["value"]["amount"] = "24.2"
    modified_body = json.dumps(payload).encode()

    async def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(
            200,
            headers={"content-type": "application/json"},
            content=modified_body,
            request=request,
        )

    async with SercopClient(
        base_url="https://sercop.test",
        transport=httpx2.MockTransport(handler),
    ) as client:
        with pytest.raises(SercopResponseError):
            await client.get_record(ocid=release["ocid"])
