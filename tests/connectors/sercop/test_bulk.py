import json
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from io import BytesIO
from typing import cast
from zipfile import ZIP_DEFLATED, ZipFile

import httpx2
import pytest

from public_intelligence.connectors.sercop import (
    SercopBulkArtifact,
    SercopBulkArtifactError,
    SercopBulkArtifactProvenance,
    SercopBulkClient,
    SercopBulkJsonError,
    SercopBulkNotFoundError,
    SercopBulkPartition,
    SercopBulkRecordError,
    SercopBulkResponseError,
    SercopTransportError,
    parse_bulk_artifact,
)

PARTITION = SercopBulkPartition(
    year=2026,
    month=7,
    procurement_type="Obra artística, científica o literaria",
)


def _zip_body(json_body: bytes) -> bytes:
    target = BytesIO()
    with ZipFile(target, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("sercop-bulk.json", json_body)
    return target.getvalue()


@pytest.mark.parametrize(
    ("values", "error_type"),
    [
        ({"year": 2014}, ValueError),
        ({"year": True}, TypeError),
        ({"month": 0}, ValueError),
        ({"month": 13}, ValueError),
        ({"month": True}, TypeError),
        ({"procurement_type": "  "}, ValueError),
        ({"procurement_type": 1}, TypeError),
    ],
)
def test_partition_validates_only_source_supported_invariants(
    values: dict[str, object],
    error_type: type[Exception],
) -> None:
    arguments: dict[str, object] = {
        "year": 2026,
        "month": 7,
        "procurement_type": "method",
    }
    arguments.update(values)

    with pytest.raises(error_type):
        SercopBulkPartition(**arguments)  # type: ignore[arg-type]


@pytest.mark.anyio
async def test_download_resolves_official_shape_and_preserves_exact_artifact(
    bulk_zip_body: bytes,
) -> None:
    requests: list[httpx2.Request] = []

    async def handler(request: httpx2.Request) -> httpx2.Response:
        requests.append(request)
        return httpx2.Response(
            200,
            headers={
                "content-type": "application/zip",
                "content-disposition": 'attachment; filename="bulk.json.zip"',
                "etag": '"artifact-etag"',
                "last-modified": "Sun, 16 Aug 2026 20:35:45 GMT",
            },
            content=bulk_zip_body,
            request=request,
        )

    async with SercopBulkClient(
        base_url="https://sercop.test",
        transport=httpx2.MockTransport(handler),
    ) as client:
        artifact = await client.download(PARTITION)

    request = requests[0]
    assert request.headers["user-agent"] == "public-intelligence"
    assert request.extensions["timeout"]["read"] == 60.0
    assert request.url.path == "/download"
    assert dict(request.url.params) == {
        "type": "json",
        "year": "2026",
        "month": "7",
        "method": "Obra artística, científica o literaria",
    }
    assert artifact.raw_body == bulk_zip_body
    assert artifact.provenance.source == "sercop"
    assert artifact.provenance.mechanism == "bulk_partition"
    assert artifact.provenance.resolved_url == str(request.url)
    assert artifact.provenance.filename == "bulk.json.zip"
    assert artifact.provenance.etag == '"artifact-etag"'
    assert artifact.provenance.last_modified == "Sun, 16 Aug 2026 20:35:45 GMT"
    assert artifact.provenance.artifact_sha256 == sha256(bulk_zip_body).hexdigest()
    assert artifact.provenance.artifact_byte_size == len(bulk_zip_body)
    assert artifact.provenance.retrieved_at.utcoffset() == timedelta(0)


@pytest.mark.anyio
async def test_bulk_default_base_url_targets_official_download(
    bulk_zip_body: bytes,
) -> None:
    requests: list[httpx2.Request] = []

    async def handler(request: httpx2.Request) -> httpx2.Response:
        requests.append(request)
        return httpx2.Response(
            200,
            headers={"content-type": "application/zip"},
            content=bulk_zip_body,
            request=request,
        )

    async with SercopBulkClient(transport=httpx2.MockTransport(handler)) as client:
        await client.download(PARTITION)

    assert requests[0].url.host == "datosabiertos.compraspublicas.gob.ec"
    assert requests[0].url.path == "/PLATAFORMA/download"


def test_parse_uses_release_package_units_and_canonical_derived_bytes(
    bulk_zip_body: bytes,
    bulk_source_packages: list[dict[str, object]],
) -> None:
    units = parse_bulk_artifact(_artifact(bulk_zip_body))

    assert len(units) == 2
    assert [unit.index for unit in units] == [0, 1]
    assert {unit.member_name for unit in units} == {"sercop-bulk.json"}
    expected = json.dumps(
        bulk_source_packages[0],
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode()
    assert units[0].canonical_body == expected
    assert units[0].canonical_body != bulk_zip_body
    assert units[0].serialization == "canonical-json-v1"
    assert units[0].source_key == units[0].data.releases[0].ocid


@pytest.mark.parametrize(
    ("ocids", "expected_source_key"),
    [
        (["ocds-valid", "ocds-valid"], "ocds-valid"),
        (["ocds-first", "ocds-second"], None),
        (["", ""], None),
        (["   ", "\t"], None),
    ],
)
def test_source_key_requires_one_shared_nonblank_ocid(
    bulk_source_packages: list[dict[str, object]],
    ocids: list[str],
    expected_source_key: str | None,
) -> None:
    package = deepcopy(bulk_source_packages[0])
    releases = cast(list[dict[str, object]], package["releases"])
    release_template = releases[0]
    package["releases"] = [
        {**release_template, "id": f"release-{index}", "ocid": ocid}
        for index, ocid in enumerate(ocids)
    ]

    unit = parse_bulk_artifact(_artifact(_zip([package])))[0]

    assert [release.ocid for release in unit.data.releases] == ocids
    assert unit.source_key == expected_source_key


def test_parse_tolerates_additive_package_fields(
    bulk_source_packages: list[dict[str, object]],
) -> None:
    packages = deepcopy(bulk_source_packages[:1])
    packages[0]["futurePackageField"] = {"preserved": True}

    unit = parse_bulk_artifact(_artifact(_zip(packages)))[0]

    assert unit.data.model_extra == {"futurePackageField": {"preserved": True}}
    assert json.loads(unit.canonical_body)["futurePackageField"] == {"preserved": True}


@pytest.mark.anyio
@pytest.mark.parametrize("status_code", [429, 500, 503])
async def test_bulk_unexpected_status_is_response_error(status_code: int) -> None:
    async def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(status_code, content=b"failure", request=request)

    async with SercopBulkClient(
        base_url="https://sercop.test",
        transport=httpx2.MockTransport(handler),
    ) as client:
        with pytest.raises(SercopBulkResponseError) as captured:
            await client.download(PARTITION)

    assert captured.value.status_code == status_code


@pytest.mark.anyio
async def test_bulk_404_is_partition_not_found() -> None:
    async def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(404, content=b"Not Found", request=request)

    async with SercopBulkClient(
        base_url="https://sercop.test",
        transport=httpx2.MockTransport(handler),
    ) as client:
        with pytest.raises(SercopBulkNotFoundError):
            await client.download(PARTITION)


@pytest.mark.anyio
async def test_bulk_success_requires_observed_zip_content_type() -> None:
    async def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(
            200,
            headers={"content-type": "application/json"},
            content=b"[]",
            request=request,
        )

    async with SercopBulkClient(
        base_url="https://sercop.test",
        transport=httpx2.MockTransport(handler),
    ) as client:
        with pytest.raises(SercopBulkResponseError, match="content type"):
            await client.download(PARTITION)


@pytest.mark.anyio
async def test_bulk_transport_failure_is_wrapped() -> None:
    async def handler(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.ConnectError("offline", request=request)

    async with SercopBulkClient(
        base_url="https://sercop.test",
        transport=httpx2.MockTransport(handler),
    ) as client:
        with pytest.raises(SercopTransportError):
            await client.download(PARTITION)


@pytest.mark.parametrize(
    ("body", "error_type"),
    [
        (b"not a zip", SercopBulkArtifactError),
        (_zip_body(b"{not-json"), SercopBulkJsonError),
        (_zip_body(b"[]"), SercopBulkArtifactError),
        (_zip_body(b"{}"), SercopBulkArtifactError),
    ],
)
def test_invalid_artifact_envelopes_fail_clearly(
    body: bytes,
    error_type: type[Exception],
) -> None:
    with pytest.raises(error_type):
        parse_bulk_artifact(_artifact(body))


def test_multiple_archive_members_are_rejected() -> None:
    target = BytesIO()
    with ZipFile(target, "w") as archive:
        archive.writestr("first.json", b"[]")
        archive.writestr("second.json", b"[]")

    with pytest.raises(SercopBulkArtifactError, match="exactly one"):
        parse_bulk_artifact(_artifact(target.getvalue()))


def test_invalid_individual_package_reports_its_index(
    bulk_source_packages: list[dict[str, object]],
) -> None:
    packages = deepcopy(bulk_source_packages)
    packages[1].pop("releases")

    with pytest.raises(SercopBulkRecordError) as captured:
        parse_bulk_artifact(_artifact(_zip(packages)))

    assert captured.value.index == 1


def _artifact(body: bytes) -> SercopBulkArtifact:
    return SercopBulkArtifact(
        raw_body=body,
        provenance=SercopBulkArtifactProvenance(
            partition=PARTITION,
            source="sercop",
            mechanism="bulk_partition",
            resolved_url="https://sercop.test/download?type=json",
            retrieved_at=datetime(2026, 8, 19, tzinfo=UTC),
            http_status=200,
            content_type="application/zip",
            filename="bulk.zip",
            etag=None,
            last_modified=None,
            artifact_sha256=sha256(body).hexdigest(),
            artifact_byte_size=len(body),
        ),
    )


def _zip(packages: list[dict[str, object]]) -> bytes:
    return _zip_body(
        json.dumps(packages, ensure_ascii=False, separators=(",", ":")).encode()
    )
