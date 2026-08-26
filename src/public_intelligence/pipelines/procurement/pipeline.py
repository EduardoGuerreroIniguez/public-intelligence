"""Explicit orchestration from one SERCOP partition to normalized facts."""

from public_intelligence.connectors.sercop import (
    SercopBulkClient,
    SercopBulkPartition,
    SercopRecordPackage,
    map_procurement_package,
)
from public_intelligence.domain.procurement import ProcurementRecord
from public_intelligence.persistence import (
    ProcurementRepository,
    RawEvidence,
    RawEvidenceRepository,
)
from public_intelligence.pipelines.sercop_bulk import ingest_partition

from .models import ProcurementProcessingSummary


class DuplicateProcurementIdentityError(ValueError):
    """Two package observations in one run map to the same normalized identity."""

    def __init__(self, *, source: str, external_id: str) -> None:
        self.source = source
        self.external_id = external_id
        super().__init__(
            "duplicate procurement identity in one processing run: "
            f"({source!r}, {external_id!r})"
        )


async def process_partition(
    partition: SercopBulkPartition,
    *,
    client: SercopBulkClient,
    raw_repository: RawEvidenceRepository,
    procurement_repository: ProcurementRepository,
) -> ProcurementProcessingSummary:
    """Process one partition completely or raise without a partial summary."""
    ingestion = await ingest_partition(
        partition,
        client=client,
        repository=raw_repository,
    )

    mapped = tuple(_map_package(evidence) for evidence in ingestion.package_evidence)
    _validate_unique_identities(mapped)

    normalized_saved = 0
    for record in mapped:
        await procurement_repository.save(record)
        normalized_saved += 1

    ingestion_summary = ingestion.summary
    return ProcurementProcessingSummary(
        partition=partition,
        ingestion_run_id=ingestion.ingestion_run_id,
        artifact_sha256=ingestion_summary.artifact_sha256,
        artifact_byte_size=ingestion_summary.artifact_byte_size,
        source_units_seen=ingestion_summary.source_units_seen,
        raw_packages_persisted=len(ingestion.package_evidence),
        mapped=len(mapped),
        normalized_saved=normalized_saved,
    )


def _map_package(evidence: RawEvidence) -> ProcurementRecord:
    package = SercopRecordPackage.model_validate_json(evidence.payload)
    return map_procurement_package(package, evidence_id=evidence.id)


def _validate_unique_identities(records: tuple[ProcurementRecord, ...]) -> None:
    seen: set[tuple[str, str]] = set()
    for record in records:
        reference = record.source_reference
        identity = (reference.source, reference.external_id)
        if identity in seen:
            raise DuplicateProcurementIdentityError(
                source=reference.source,
                external_id=reference.external_id,
            )
        seen.add(identity)
