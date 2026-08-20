"""Immutable outcome models for bounded SERCOP bulk ingestion."""

from dataclasses import dataclass

from public_intelligence.connectors.sercop import SercopBulkPartition


@dataclass(frozen=True, slots=True)
class SercopBulkIngestionSummary:
    """Successful source-unit counts; the separately stored artifact is excluded."""

    partition: SercopBulkPartition
    artifact_sha256: str
    artifact_byte_size: int
    source_units_seen: int
    persisted: int
    failed: int
