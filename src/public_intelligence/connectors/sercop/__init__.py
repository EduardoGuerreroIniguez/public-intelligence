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
    SercopAmbiguousProcurementIdentityError,
    SercopBulkArtifactError,
    SercopBulkError,
    SercopBulkJsonError,
    SercopBulkNotFoundError,
    SercopBulkRecordError,
    SercopBulkResponseError,
    SercopError,
    SercopInvalidDateError,
    SercopInvalidMoneyError,
    SercopMissingProcurementIdentityError,
    SercopNotFoundError,
    SercopProcurementMappingError,
    SercopResponseError,
    SercopTransportError,
    SercopUnsupportedReleaseStructureError,
)
from .models import SercopRecordPackage, SercopSearchPage, SercopSearchSummary
from .procurement_mapper import map_procurement_package
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
    "SercopAmbiguousProcurementIdentityError",
    "SercopInvalidDateError",
    "SercopInvalidMoneyError",
    "SercopMissingProcurementIdentityError",
    "SercopNotFoundError",
    "SercopProcurementMappingError",
    "SercopProvenance",
    "SercopRecordPackage",
    "SercopResponseError",
    "SercopResult",
    "SercopSearchPage",
    "SercopSearchSummary",
    "SercopTransportError",
    "SercopUnsupportedReleaseStructureError",
    "map_procurement_package",
    "parse_bulk_artifact",
]
