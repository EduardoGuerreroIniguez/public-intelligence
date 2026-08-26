"""Immutable outcome models for end-to-end procurement processing."""

from dataclasses import dataclass
from uuid import UUID

from public_intelligence.connectors.sercop import SercopBulkPartition


@dataclass(frozen=True, slots=True)
class ProcurementProcessingSummary:
    """Counts from one completely successful partition-processing run."""

    partition: SercopBulkPartition
    ingestion_run_id: UUID
    artifact_sha256: str
    artifact_byte_size: int
    source_units_seen: int
    raw_packages_persisted: int
    mapped: int
    normalized_saved: int
