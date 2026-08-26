"""Persisted metadata for normalized procurement snapshots."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from public_intelligence.domain.procurement import ProcurementRecord


@dataclass(frozen=True, slots=True)
class StoredProcurement:
    """A normalized procurement snapshot with persistence-owned metadata."""

    id: UUID
    record: ProcurementRecord
    created_at: datetime
    updated_at: datetime
