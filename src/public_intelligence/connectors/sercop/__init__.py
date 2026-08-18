"""Source-specific SERCOP connector public interface."""

from .client import SERCOP_BASE_URL, SercopClient
from .errors import (
    SercopError,
    SercopNotFoundError,
    SercopResponseError,
    SercopTransportError,
)
from .models import SercopRecordPackage, SercopSearchPage, SercopSearchSummary
from .provenance import SercopProvenance, SercopResult

__all__ = [
    "SERCOP_BASE_URL",
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
]
