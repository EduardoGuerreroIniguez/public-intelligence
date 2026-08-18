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
