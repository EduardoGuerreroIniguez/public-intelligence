"""Explicit orchestration for one SERCOP bulk partition."""

from hashlib import sha256
from uuid import uuid4

from public_intelligence.connectors.sercop import (
    SercopBulkClient,
    SercopBulkPartition,
    parse_bulk_artifact,
)
from public_intelligence.persistence import RawEvidenceInput, RawEvidenceRepository

from .models import SercopBulkIngestionResult, SercopBulkIngestionSummary

PACKAGE_MECHANISM = "bulk_partition_release_package"


async def ingest_partition(
    partition: SercopBulkPartition,
    *,
    client: SercopBulkClient,
    repository: RawEvidenceRepository,
) -> SercopBulkIngestionResult:
    """Download, validate, and atomically persist one explicit partition."""
    artifact = await client.download(partition)
    source_units = parse_bulk_artifact(artifact)
    provenance = artifact.provenance
    ingestion_run_id = uuid4()

    artifact_parameters: dict[str, object] = {
        "type": "json",
        "year": partition.year,
        "month": partition.month,
        "method": partition.procurement_type,
        "ingestion_run_id": str(ingestion_run_id),
    }
    if provenance.filename is not None:
        artifact_parameters["filename"] = provenance.filename

    evidence: list[RawEvidenceInput] = [
        RawEvidenceInput(
            source=provenance.source,
            mechanism=provenance.mechanism,
            source_key=None,
            endpoint=provenance.resolved_url,
            parameters=artifact_parameters,
            retrieved_at=provenance.retrieved_at,
            http_status=provenance.http_status,
            content_type=provenance.content_type,
            payload_sha256=provenance.artifact_sha256,
            payload_byte_size=provenance.artifact_byte_size,
            payload=artifact.raw_body,
            etag=provenance.etag,
            last_modified=provenance.last_modified,
        )
    ]

    for source_unit in source_units:
        canonical_body = source_unit.canonical_body
        evidence.append(
            RawEvidenceInput(
                source="sercop",
                mechanism=PACKAGE_MECHANISM,
                source_key=source_unit.source_key,
                endpoint=provenance.resolved_url,
                parameters={
                    "type": "json",
                    "year": partition.year,
                    "month": partition.month,
                    "method": partition.procurement_type,
                    "ingestion_run_id": str(ingestion_run_id),
                    "artifact": {
                        "sha256": provenance.artifact_sha256,
                        "byte_size": provenance.artifact_byte_size,
                        "member": source_unit.member_name,
                        "source_unit_index": source_unit.index,
                    },
                    "serialization": source_unit.serialization,
                },
                retrieved_at=provenance.retrieved_at,
                http_status=provenance.http_status,
                content_type="application/json",
                payload_sha256=sha256(canonical_body).hexdigest(),
                payload_byte_size=len(canonical_body),
                payload=canonical_body,
            )
        )

    stored = await repository.save_many(evidence)
    package_evidence = stored[1:]
    return SercopBulkIngestionResult(
        summary=SercopBulkIngestionSummary(
            partition=partition,
            artifact_sha256=provenance.artifact_sha256,
            artifact_byte_size=provenance.artifact_byte_size,
            source_units_seen=len(source_units),
            persisted=len(package_evidence),
            failed=0,
        ),
        ingestion_run_id=ingestion_run_id,
        package_evidence=package_evidence,
    )
