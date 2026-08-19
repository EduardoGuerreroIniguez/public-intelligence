"""Source-neutral raw evidence input and persisted representations."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class RawEvidenceInput:
    """Exact source evidence and provenance presented for persistence."""

    source: str
    mechanism: str
    source_key: str | None
    endpoint: str
    parameters: Mapping[str, object]
    retrieved_at: datetime
    http_status: int
    content_type: str
    payload_sha256: str
    payload_byte_size: int
    payload: bytes
    etag: str | None = None
    last_modified: str | None = None


@dataclass(frozen=True, slots=True)
class RawEvidence:
    """A persisted raw evidence observation."""

    id: UUID
    source: str
    mechanism: str
    source_key: str | None
    endpoint: str
    parameters: Mapping[str, object]
    retrieved_at: datetime
    http_status: int
    content_type: str
    payload_sha256: str
    payload_byte_size: int
    payload: bytes
    etag: str | None
    last_modified: str | None
    created_at: datetime
