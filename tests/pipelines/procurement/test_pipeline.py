import json
from copy import deepcopy
from io import BytesIO
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile

import httpx2
import psycopg
import pytest

from public_intelligence.connectors.sercop import (
    SercopBulkClient,
    SercopBulkNotFoundError,
    SercopBulkPartition,
    SercopUnsupportedReleaseStructureError,
)
from public_intelligence.persistence import (
    PostgresDatabase,
    ProcurementRepository,
    RawEvidenceRepository,
)
from public_intelligence.pipelines.procurement import (
    DuplicateProcurementIdentityError,
    process_partition,
)

PARTITION = SercopBulkPartition(
    year=2026,
    month=7,
    procurement_type="Obra artística, científica o literaria",
)
RESPONSE_HEADERS = {
    "content-type": "application/zip",
    "content-disposition": 'attachment; filename="sercop-partition.zip"',
    "etag": '"bulk-etag"',
    "last-modified": "Sun, 16 Aug 2026 20:35:45 GMT",
}


@pytest.mark.anyio
async def test_partition_processes_raw_packages_into_normalized_procurements(
    database: PostgresDatabase,
    bulk_zip_body: bytes,
) -> None:
    client = _client(bulk_zip_body)
    async with client:
        summary = await process_partition(
            PARTITION,
            client=client,
            raw_repository=RawEvidenceRepository(database),
            procurement_repository=ProcurementRepository(database),
        )

    raw_rows = await _raw_rows(database)
    normalized_rows = await _normalized_rows(database)
    package_rows = [
        row for row in raw_rows if row["mechanism"] == "bulk_partition_release_package"
    ]
    artifact_rows = [row for row in raw_rows if row["mechanism"] == "bulk_partition"]

    assert summary.partition == PARTITION
    assert summary.source_units_seen == 2
    assert summary.raw_packages_persisted == 2
    assert summary.mapped == 2
    assert summary.normalized_saved == 2
    assert not hasattr(summary, "failed")
    assert len(raw_rows) == 3
    assert len(package_rows) == 2
    assert len(artifact_rows) == 1
    assert len(normalized_rows) == 2
    assert {row["evidence_id"] for row in normalized_rows} == {
        row["id"] for row in package_rows
    }
    assert artifact_rows[0]["id"] not in {row["evidence_id"] for row in normalized_rows}
    assert {row["parameters"]["ingestion_run_id"] for row in raw_rows} == {
        str(summary.ingestion_run_id)
    }


@pytest.mark.anyio
async def test_duplicate_identity_in_one_run_fails_before_normalized_save(
    database: PostgresDatabase,
    bulk_source_packages: list[dict[str, object]],
) -> None:
    duplicate_packages = [
        deepcopy(bulk_source_packages[0]),
        deepcopy(bulk_source_packages[0]),
    ]
    client = _client(_zip(duplicate_packages))

    async with client:
        with pytest.raises(DuplicateProcurementIdentityError) as captured:
            await process_partition(
                PARTITION,
                client=client,
                raw_repository=RawEvidenceRepository(database),
                procurement_repository=ProcurementRepository(database),
            )

    assert captured.value.source == "sercop"
    assert captured.value.external_id.startswith("ocds-5wno2w-")
    assert await _table_count(database, "raw_evidence") == 3
    assert await _table_count(database, "procurements") == 0


@pytest.mark.anyio
async def test_mapping_failure_preserves_raw_and_writes_no_normalized_rows(
    database: PostgresDatabase,
    bulk_source_packages: list[dict[str, object]],
) -> None:
    package = deepcopy(bulk_source_packages[0])
    releases = package["releases"]
    assert isinstance(releases, list)
    releases.append(deepcopy(releases[0]))
    client = _client(_zip([package]))

    async with client:
        with pytest.raises(SercopUnsupportedReleaseStructureError):
            await process_partition(
                PARTITION,
                client=client,
                raw_repository=RawEvidenceRepository(database),
                procurement_repository=ProcurementRepository(database),
            )

    assert await _table_count(database, "raw_evidence") == 2
    assert await _table_count(database, "procurements") == 0


@pytest.mark.anyio
async def test_normalized_child_failure_preserves_raw_and_rolls_back_record(
    database: PostgresDatabase,
    bulk_source_packages: list[dict[str, object]],
) -> None:
    valid_package = deepcopy(bulk_source_packages[0])
    invalid_package = deepcopy(bulk_source_packages[1])
    releases = invalid_package["releases"]
    assert isinstance(releases, list)
    release = releases[0]
    assert isinstance(release, dict)
    release["awards"] = [
        {
            "id": "award-with-invalid-supplier",
            "suppliers": [{"id": "supplier", "name": "contains\x00nul"}],
        }
    ]
    client = _client(_zip([valid_package, invalid_package]))

    async with client:
        with pytest.raises(psycopg.DataError):
            await process_partition(
                PARTITION,
                client=client,
                raw_repository=RawEvidenceRepository(database),
                procurement_repository=ProcurementRepository(database),
            )

    normalized_rows = await _normalized_rows(database)
    assert await _table_count(database, "raw_evidence") == 3
    assert len(normalized_rows) == 1
    valid_releases = valid_package["releases"]
    assert isinstance(valid_releases, list)
    valid_release = valid_releases[0]
    assert isinstance(valid_release, dict)
    assert normalized_rows[0]["external_id"] == valid_release["ocid"]


@pytest.mark.anyio
async def test_raw_ingestion_failure_propagates_without_normalization(
    database: PostgresDatabase,
) -> None:
    async def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(404, request=request)

    client = SercopBulkClient(
        base_url="https://sercop.test",
        transport=httpx2.MockTransport(handler),
    )
    async with client:
        with pytest.raises(SercopBulkNotFoundError):
            await process_partition(
                PARTITION,
                client=client,
                raw_repository=RawEvidenceRepository(database),
                procurement_repository=ProcurementRepository(database),
            )

    assert await _table_count(database, "raw_evidence") == 0
    assert await _table_count(database, "procurements") == 0


@pytest.mark.anyio
async def test_rerun_preserves_raw_observations_and_replaces_normalized_evidence(
    database: PostgresDatabase,
    bulk_zip_body: bytes,
) -> None:
    raw_repository = RawEvidenceRepository(database)
    procurement_repository = ProcurementRepository(database)
    first_client = _client(bulk_zip_body)
    second_client = _client(bulk_zip_body)

    async with first_client:
        first = await process_partition(
            PARTITION,
            client=first_client,
            raw_repository=raw_repository,
            procurement_repository=procurement_repository,
        )
    first_normalized = await _normalized_rows(database)

    async with second_client:
        second = await process_partition(
            PARTITION,
            client=second_client,
            raw_repository=raw_repository,
            procurement_repository=procurement_repository,
        )
    second_normalized = await _normalized_rows(database)
    second_evidence = await _package_ids_for_run(database, second.ingestion_run_id)

    assert first.ingestion_run_id != second.ingestion_run_id
    assert await _table_count(database, "raw_evidence") == 6
    assert await _table_count(database, "procurements") == 2
    assert {row["external_id"]: row["id"] for row in first_normalized} == {
        row["external_id"]: row["id"] for row in second_normalized
    }
    assert {row["evidence_id"] for row in second_normalized} == second_evidence
    assert {row["evidence_id"] for row in first_normalized}.isdisjoint(second_evidence)


def _client(body: bytes) -> SercopBulkClient:
    async def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(
            200,
            headers=RESPONSE_HEADERS,
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


async def _raw_rows(database: PostgresDatabase) -> list[dict[str, Any]]:
    async with database.connection() as connection:
        rows = await (
            await connection.execute(
                "SELECT * FROM raw_evidence ORDER BY created_at, id"
            )
        ).fetchall()
    return [dict(row) for row in rows]


async def _normalized_rows(database: PostgresDatabase) -> list[dict[str, Any]]:
    async with database.connection() as connection:
        rows = await (
            await connection.execute(
                "SELECT id, external_id, evidence_id FROM procurements "
                "ORDER BY external_id"
            )
        ).fetchall()
    return [dict(row) for row in rows]


async def _package_ids_for_run(
    database: PostgresDatabase,
    ingestion_run_id: object,
) -> set[object]:
    async with database.connection() as connection:
        rows = await (
            await connection.execute(
                """
                SELECT id
                FROM raw_evidence
                WHERE mechanism = 'bulk_partition_release_package'
                  AND parameters->>'ingestion_run_id' = %(ingestion_run_id)s
                """,
                {"ingestion_run_id": str(ingestion_run_id)},
            )
        ).fetchall()
    return {row["id"] for row in rows}


async def _table_count(database: PostgresDatabase, table_name: str) -> int:
    if table_name not in {"raw_evidence", "procurements"}:
        raise ValueError("unsupported test table")
    query = (
        "SELECT count(*) AS count FROM raw_evidence"
        if table_name == "raw_evidence"
        else "SELECT count(*) AS count FROM procurements"
    )
    async with database.connection() as connection:
        row = await (await connection.execute(query)).fetchone()
    assert row is not None
    return row["count"]
