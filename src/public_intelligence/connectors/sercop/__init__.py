"""Source-specific SERCOP connector public interface."""

from .bulk import (
    SercopBulkArtifact,
    SercopBulkArtifactProvenance,
    SercopBulkClient,
    SercopBulkPartition,
    SercopBulkSourceUnit,
    parse_bulk_artifact,
)
from .client import SERCOP_BASE_URL, SercopClient
from .errors import (
    SercopBulkArtifactError,
    SercopBulkError,
    SercopBulkJsonError,
    SercopBulkNotFoundError,
    SercopBulkRecordError,
    SercopBulkResponseError,
    SercopError,
    SercopNotFoundError,
    SercopResponseError,
    SercopTransportError,
)
from .models import SercopRecordPackage, SercopSearchPage, SercopSearchSummary
from .provenance import SercopProvenance, SercopResult

__all__ = [
    "SERCOP_BASE_URL",
    "SercopBulkArtifact",
    "SercopBulkArtifactError",
    "SercopBulkArtifactProvenance",
    "SercopBulkClient",
    "SercopBulkError",
    "SercopBulkJsonError",
    "SercopBulkNotFoundError",
    "SercopBulkPartition",
    "SercopBulkRecordError",
    "SercopBulkResponseError",
    "SercopBulkSourceUnit",
    "SercopClient",
    "SercopError",
    "SercopNotFoundError",
    "SercopProvenance",
    "SercopRecordPackage",
    "SercopResponseError",
    "SercopResult",
    "SercopSearchPage",
    "SercopSearchSummary",
    "SercopTransportError",
    "parse_bulk_artifact",
]
