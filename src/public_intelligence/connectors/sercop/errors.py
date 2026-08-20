"""Source-specific errors raised by the SERCOP connector."""


class SercopError(Exception):
    """Base error for SERCOP connector failures."""


class SercopNotFoundError(SercopError):
    """A requested SERCOP record was not found."""

    def __init__(self, *, ocid: str, endpoint: str, status_code: int) -> None:
        self.ocid = ocid
        self.endpoint = endpoint
        self.status_code = status_code
        super().__init__(f"SERCOP record not found for OCID {ocid!r}")


class SercopResponseError(SercopError):
    """SERCOP returned a response the connector cannot accept."""

    def __init__(
        self,
        *,
        endpoint: str,
        reason: str,
        status_code: int | None = None,
        content_type: str | None = None,
    ) -> None:
        self.endpoint = endpoint
        self.reason = reason
        self.status_code = status_code
        self.content_type = content_type
        status = f" with HTTP {status_code}" if status_code is not None else ""
        super().__init__(f"Invalid SERCOP response from {endpoint}{status}: {reason}")


class SercopTransportError(SercopError):
    """A SERCOP request could not be completed by the HTTP transport."""

    def __init__(self, *, endpoint: str, reason: str) -> None:
        self.endpoint = endpoint
        self.reason = reason
        super().__init__(f"SERCOP transport failure for {endpoint}: {reason}")


class SercopBulkError(SercopError):
    """Base error for SERCOP bulk-partition failures."""


class SercopBulkNotFoundError(SercopBulkError):
    """The explicitly requested SERCOP bulk partition was not found."""

    def __init__(self, *, endpoint: str, status_code: int) -> None:
        self.endpoint = endpoint
        self.status_code = status_code
        super().__init__(f"SERCOP bulk partition not found at {endpoint}")


class SercopBulkResponseError(SercopBulkError):
    """SERCOP returned an unacceptable bulk HTTP response."""

    def __init__(
        self,
        *,
        endpoint: str,
        reason: str,
        status_code: int,
        content_type: str | None = None,
    ) -> None:
        self.endpoint = endpoint
        self.reason = reason
        self.status_code = status_code
        self.content_type = content_type
        super().__init__(
            f"Invalid SERCOP bulk response from {endpoint} "
            f"with HTTP {status_code}: {reason}"
        )


class SercopBulkArtifactError(SercopBulkError):
    """The downloaded bulk artifact does not match the observed ZIP shape."""


class SercopBulkJsonError(SercopBulkArtifactError):
    """The JSON member in a SERCOP bulk artifact is malformed."""


class SercopBulkRecordError(SercopBulkError):
    """One indexed release package in the bulk artifact is invalid."""

    def __init__(self, *, index: int, reason: str) -> None:
        self.index = index
        self.reason = reason
        super().__init__(f"Invalid SERCOP bulk source unit at index {index}: {reason}")


class SercopProcurementMappingError(SercopError):
    """Base error for translating validated SERCOP data into procurement facts."""


class SercopMissingProcurementIdentityError(SercopProcurementMappingError):
    """A release package has no usable procurement identity."""

    def __init__(self) -> None:
        super().__init__("SERCOP release package has a blank procurement identity")


class SercopAmbiguousProcurementIdentityError(SercopProcurementMappingError):
    """A release package contains more than one procurement identity."""

    def __init__(self, *, ocids: tuple[str, ...]) -> None:
        self.ocids = ocids
        super().__init__("SERCOP release package contains distinct OCIDs")


class SercopUnsupportedReleaseStructureError(SercopProcurementMappingError):
    """A release package cannot be mapped without an unsupported merge rule."""

    def __init__(self, *, reason: str) -> None:
        self.reason = reason
        super().__init__(f"Unsupported SERCOP release structure: {reason}")


class SercopInvalidMoneyError(SercopProcurementMappingError):
    """A modeled SERCOP monetary value is unusable."""

    def __init__(self, *, field: str) -> None:
        self.field = field
        super().__init__(f"Invalid SERCOP monetary value at {field}")


class SercopInvalidDateError(SercopProcurementMappingError):
    """A modeled SERCOP datetime is invalid or lacks a source timezone."""

    def __init__(self, *, field: str) -> None:
        self.field = field
        super().__init__(f"Invalid SERCOP datetime at {field}")
