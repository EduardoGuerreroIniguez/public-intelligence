"""Manual orchestration for one bounded SERCOP bulk partition."""

from .models import SercopBulkIngestionSummary
from .pipeline import ingest_partition

__all__ = ["SercopBulkIngestionSummary", "ingest_partition"]
