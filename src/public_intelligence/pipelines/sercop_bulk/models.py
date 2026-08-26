"""Immutable outcome models for bounded SERCOP bulk ingestion."""

from dataclasses import dataclass
from uuid import UUID

from public_intelligence.connectors.sercop import SercopBulkPartition
from public_intelligence.persistence import RawEvidence


@dataclass(frozen=True, slots=True)
class SercopBulkIngestionSummary:
    """Successful source-unit counts; the separately stored artifact is excluded."""

    partition: SercopBulkPartition
    artifact_sha256: str
    artifact_byte_size: int
    source_units_seen: int
    persisted: int
    failed: int


@dataclass(frozen=True, slots=True)
class SercopBulkIngestionResult:
    """Summary and newly stored package evidence from one bounded operation."""

    summary: SercopBulkIngestionSummary
    ingestion_run_id: UUID
    package_evidence: tuple[RawEvidence, ...]
