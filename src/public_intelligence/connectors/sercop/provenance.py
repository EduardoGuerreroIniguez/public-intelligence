"""Raw evidence and provenance returned by the SERCOP connector."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

RequestParameter = str | int
SercopAccessMechanism = Literal["keyword_search", "ocid_record"]


@dataclass(frozen=True, slots=True)
class SercopProvenance:
    """Metadata describing a successful SERCOP source retrieval."""

    source_key: Literal["sercop"]
    access_mechanism: SercopAccessMechanism
    endpoint: str
    request_parameters: Mapping[str, RequestParameter]
    retrieved_at: datetime
    http_status: int
    content_type: str
    payload_sha256: str
    payload_size: int
    last_modified: str | None
    etag: str | None


@dataclass(frozen=True, slots=True)
class SercopResult[T]:
    """Typed source data accompanied by its raw evidence and provenance."""

    data: T
    raw_body: bytes
    provenance: SercopProvenance
