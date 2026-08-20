"""Bounded access to the SERCOP bulk JSON publication."""

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from email.message import Message
from hashlib import sha256
from io import BytesIO
from typing import Literal
from zipfile import BadZipFile, ZipFile

import httpx2
from pydantic import ValidationError

from .client import SERCOP_BASE_URL, USER_AGENT
from .errors import (
    SercopBulkArtifactError,
    SercopBulkJsonError,
    SercopBulkNotFoundError,
    SercopBulkRecordError,
    SercopBulkResponseError,
    SercopTransportError,
)
from .models import SercopRecordPackage

DEFAULT_BULK_TIMEOUT_SECONDS = 60.0

_BULK_ENDPOINT = "/download"
_CANONICAL_SERIALIZATION = "canonical-json-v1"


@dataclass(frozen=True, slots=True)
class SercopBulkPartition:
    """One explicit SERCOP bulk partition."""

    year: int
    month: int
    procurement_type: str

    def __post_init__(self) -> None:
        if isinstance(self.year, bool) or not isinstance(self.year, int):
            raise TypeError("year must be an integer")
        if self.year < 2015:
            raise ValueError("year must be 2015 or later")
        if isinstance(self.month, bool) or not isinstance(self.month, int):
            raise TypeError("month must be an integer")
        if not 1 <= self.month <= 12:
            raise ValueError("month must be between 1 and 12")
        if not isinstance(self.procurement_type, str):
            raise TypeError("procurement_type must be a string")
        if not self.procurement_type.strip():
            raise ValueError("procurement_type must not be blank")


@dataclass(frozen=True, slots=True)
class SercopBulkArtifactProvenance:
    """Provenance for the exact downloaded ZIP response bytes."""

    partition: SercopBulkPartition
    source: Literal["sercop"]
    mechanism: Literal["bulk_partition"]
    resolved_url: str
    retrieved_at: datetime
    http_status: int
    content_type: str
    filename: str | None
    etag: str | None
    last_modified: str | None
    artifact_sha256: str
    artifact_byte_size: int


@dataclass(frozen=True, slots=True)
class SercopBulkArtifact:
    """Exact HTTP response bytes for one bulk-partition ZIP artifact."""

    raw_body: bytes
    provenance: SercopBulkArtifactProvenance


@dataclass(frozen=True, slots=True)
class SercopBulkSourceUnit:
    """One release package and its deterministic derived JSON bytes."""

    index: int
    member_name: str
    data: SercopRecordPackage
    canonical_body: bytes
    source_key: str | None
    serialization: str = _CANONICAL_SERIALIZATION


class SercopBulkClient:
    """Async client for downloading one explicit SERCOP JSON partition."""

    def __init__(
        self,
        *,
        base_url: str = SERCOP_BASE_URL,
        timeout_seconds: float = DEFAULT_BULK_TIMEOUT_SECONDS,
        transport: httpx2.AsyncBaseTransport | None = None,
    ) -> None:
        self._client = httpx2.AsyncClient(
            base_url=base_url.rstrip("/"),
            headers={"User-Agent": USER_AGENT},
            timeout=timeout_seconds,
            transport=transport,
        )

    async def __aenter__(self) -> "SercopBulkClient":
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: object | None,
    ) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        """Close the owned HTTP connection pool."""
        await self._client.aclose()

    async def download(self, partition: SercopBulkPartition) -> SercopBulkArtifact:
        """Download and buffer the exact ZIP bytes for one bounded partition."""
        parameters: dict[str, str | int] = {
            "type": "json",
            "year": partition.year,
            "month": partition.month,
            "method": partition.procurement_type,
        }
        try:
            response = await self._client.get(_BULK_ENDPOINT, params=parameters)
        except httpx2.RequestError as error:
            raise SercopTransportError(
                endpoint=_BULK_ENDPOINT,
                reason=str(error) or error.__class__.__name__,
            ) from error

        resolved_url = str(response.request.url)
        content_type = response.headers.get("content-type", "")
        if response.status_code == 404:
            raise SercopBulkNotFoundError(
                endpoint=resolved_url,
                status_code=response.status_code,
            )
        if not 200 <= response.status_code < 300:
            raise SercopBulkResponseError(
                endpoint=resolved_url,
                status_code=response.status_code,
                content_type=content_type or None,
                reason="unexpected HTTP status",
            )

        media_type = content_type.partition(";")[0].strip().lower()
        if media_type != "application/zip":
            raise SercopBulkResponseError(
                endpoint=resolved_url,
                status_code=response.status_code,
                content_type=content_type or None,
                reason="unexpected successful content type",
            )

        raw_body = response.content
        provenance = SercopBulkArtifactProvenance(
            partition=partition,
            source="sercop",
            mechanism="bulk_partition",
            resolved_url=resolved_url,
            retrieved_at=datetime.now(UTC),
            http_status=response.status_code,
            content_type=content_type,
            filename=_response_filename(response.headers.get("content-disposition")),
            etag=response.headers.get("etag"),
            last_modified=response.headers.get("last-modified"),
            artifact_sha256=sha256(raw_body).hexdigest(),
            artifact_byte_size=len(raw_body),
        )
        return SercopBulkArtifact(raw_body=raw_body, provenance=provenance)


def parse_bulk_artifact(
    artifact: SercopBulkArtifact,
) -> tuple[SercopBulkSourceUnit, ...]:
    """Parse only the one-member ZIP and package-array shape observed by SPEC-002."""
    try:
        with ZipFile(BytesIO(artifact.raw_body)) as archive:
            members = [member for member in archive.infolist() if not member.is_dir()]
            if len(members) != 1 or not members[0].filename.lower().endswith(".json"):
                raise SercopBulkArtifactError(
                    "bulk ZIP must contain exactly one JSON member"
                )
            member = members[0]
            json_body = archive.read(member)
    except BadZipFile as error:
        raise SercopBulkArtifactError(
            "bulk response is not a valid ZIP archive"
        ) from error

    try:
        payload = json.loads(json_body, parse_constant=_reject_json_constant)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise SercopBulkJsonError("bulk JSON member is malformed") from error

    if not isinstance(payload, list) or not payload:
        raise SercopBulkArtifactError(
            "bulk JSON member must be a non-empty array of release packages"
        )

    source_units: list[SercopBulkSourceUnit] = []
    for index, source_package in enumerate(payload):
        if not isinstance(source_package, dict):
            raise SercopBulkRecordError(
                index=index,
                reason="source unit must be a JSON object",
            )
        try:
            data = SercopRecordPackage.model_validate(source_package)
            canonical_body = json.dumps(
                source_package,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            ).encode("utf-8")
        except ValidationError as error:
            raise SercopBulkRecordError(
                index=index,
                reason="release package does not match the observed source contract",
            ) from error
        except (TypeError, ValueError) as error:
            raise SercopBulkRecordError(
                index=index,
                reason="release package cannot be serialized deterministically",
            ) from error

        release_ocids = [release.ocid for release in data.releases]
        distinct_ocids = set(release_ocids)
        source_key = None
        if all(ocid.strip() for ocid in release_ocids) and len(distinct_ocids) == 1:
            source_key = next(iter(distinct_ocids))
        source_units.append(
            SercopBulkSourceUnit(
                index=index,
                member_name=member.filename,
                data=data,
                canonical_body=canonical_body,
                source_key=source_key,
            )
        )

    return tuple(source_units)


def _response_filename(content_disposition: str | None) -> str | None:
    if content_disposition is None:
        return None
    message = Message()
    message["content-disposition"] = content_disposition
    return message.get_filename()


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"non-standard JSON constant {value!r}")
