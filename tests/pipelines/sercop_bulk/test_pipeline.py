import json
from copy import deepcopy
from hashlib import sha256
from io import BytesIO
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile

import httpx2
import pytest

from public_intelligence.connectors.sercop import (
    SercopBulkClient,
    SercopBulkPartition,
    SercopBulkRecordError,
)
from public_intelligence.persistence import PostgresDatabase, RawEvidenceRepository
from public_intelligence.pipelines.sercop_bulk import ingest_partition

PARTITION = SercopBulkPartition(
    year=2026,
    month=7,
    procurement_type="Obra artística, científica o literaria",
)


@pytest.mark.anyio
async def test_partition_ingests_exact_artifact_and_derived_packages_atomically(
    database: PostgresDatabase,
    bulk_zip_body: bytes,
    bulk_response_headers: dict[str, str],
) -> None:
    client = _client(bulk_zip_body, bulk_response_headers)
    async with client:
        summary = await ingest_partition(
            PARTITION,
            client=client,
            repository=RawEvidenceRepository(database),
        )

    rows = await _rows(database)
    assert summary.partition == PARTITION
    assert summary.artifact_sha256 == sha256(bulk_zip_body).hexdigest()
    assert summary.artifact_byte_size == len(bulk_zip_body)
    assert summary.source_units_seen == 2
    assert summary.persisted == 2
    assert summary.failed == 0
    assert len(rows) == 3

    artifact_rows = [row for row in rows if row["mechanism"] == "bulk_partition"]
    package_rows = sorted(
        (row for row in rows if row["mechanism"] == "bulk_partition_release_package"),
        key=lambda row: row["parameters"]["artifact"]["source_unit_index"],
    )
    assert len(artifact_rows) == 1
    assert len(package_rows) == 2

    artifact = artifact_rows[0]
    assert bytes(artifact["payload"]) == bulk_zip_body
    assert artifact["payload_sha256"] == sha256(bulk_zip_body).hexdigest()
    assert artifact["payload_byte_size"] == len(bulk_zip_body)
    assert artifact["content_type"] == "application/zip"
    assert artifact["source_key"] is None
    assert artifact["etag"] == '"bulk-etag"'
    assert artifact["last_modified"] == "Sun, 16 Aug 2026 20:35:45 GMT"
    assert artifact["parameters"]["filename"] == "sercop-partition.zip"

    ingestion_run_id = artifact["parameters"]["ingestion_run_id"]
    for index, package in enumerate(package_rows):
        package_body = bytes(package["payload"])
        assert package_body != bulk_zip_body
        assert json.loads(package_body)["releases"]
        assert package["payload_sha256"] == sha256(package_body).hexdigest()
        assert package["payload_byte_size"] == len(package_body)
        assert package["content_type"] == "application/json"
        assert package["source_key"].startswith("ocds-5wno2w-")
        assert package["etag"] is None
        assert package["last_modified"] is None
        assert package["parameters"]["ingestion_run_id"] == ingestion_run_id
        assert package["parameters"]["serialization"] == "canonical-json-v1"
        assert package["parameters"]["artifact"] == {
            "sha256": summary.artifact_sha256,
            "byte_size": summary.artifact_byte_size,
            "member": "sercop-bulk.json",
            "source_unit_index": index,
        }


@pytest.mark.anyio
async def test_malformed_record_fails_before_any_partition_row_is_inserted(
    database: PostgresDatabase,
    bulk_source_packages: list[dict[str, object]],
    bulk_response_headers: dict[str, str],
) -> None:
    packages = deepcopy(bulk_source_packages)
    packages[1].pop("releases")
    client = _client(_zip(packages), bulk_response_headers)

    async with client:
        with pytest.raises(SercopBulkRecordError) as captured:
            await ingest_partition(
                PARTITION,
                client=client,
                repository=RawEvidenceRepository(database),
            )

    assert captured.value.index == 1
    assert await _row_count(database) == 0


@pytest.mark.anyio
async def test_duplicate_partition_rerun_persists_independent_observations(
    database: PostgresDatabase,
    bulk_zip_body: bytes,
    bulk_response_headers: dict[str, str],
) -> None:
    repository = RawEvidenceRepository(database)
    first_client = _client(bulk_zip_body, bulk_response_headers)
    second_client = _client(bulk_zip_body, bulk_response_headers)

    async with first_client:
        first = await ingest_partition(
            PARTITION,
            client=first_client,
            repository=repository,
        )
    async with second_client:
        second = await ingest_partition(
            PARTITION,
            client=second_client,
            repository=repository,
        )

    rows = await _rows(database)
    run_ids = {row["parameters"]["ingestion_run_id"] for row in rows}
    assert first.artifact_sha256 == second.artifact_sha256
    assert first.persisted == second.persisted == 2
    assert len(rows) == 6
    assert len(run_ids) == 2
    assert len({row["id"] for row in rows}) == 6


def _client(body: bytes, headers: dict[str, str]) -> SercopBulkClient:
    async def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(
            200,
            headers=headers,
            content=body,
            request=request,
        )

    return SercopBulkClient(
        base_url="https://sercop.test",
        transport=httpx2.MockTransport(handler),
    )


def _zip(packages: list[dict[str, object]]) -> bytes:
    target = BytesIO()
    with ZipFile(target, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr(
            "sercop-bulk.json",
            json.dumps(packages, ensure_ascii=False, separators=(",", ":")).encode(),
        )
    return target.getvalue()


async def _rows(database: PostgresDatabase) -> list[dict[str, Any]]:
    async with database.connection() as connection:
        cursor = await connection.execute(
            """
            SELECT *
            FROM raw_evidence
            ORDER BY created_at, id
            """
        )
        rows = await cursor.fetchall()
    return [dict(row) for row in rows]


async def _row_count(database: PostgresDatabase) -> int:
    async with database.connection() as connection:
        row = await (
            await connection.execute("SELECT count(*) AS count FROM raw_evidence")
        ).fetchone()
    assert row is not None
    return row["count"]
