"""Asynchronous targeted-access client for SERCOP open data."""

from collections.abc import Mapping
from datetime import UTC, datetime
from hashlib import sha256
from types import MappingProxyType
from typing import TypeVar

import httpx2
from pydantic import BaseModel, ValidationError

from .errors import (
    SercopNotFoundError,
    SercopResponseError,
    SercopTransportError,
)
from .models import SercopRecordPackage, SercopSearchPage
from .provenance import RequestParameter, SercopAccessMechanism, SercopProvenance
from .provenance import SercopResult as Result

SERCOP_BASE_URL = "https://datosabiertos.compraspublicas.gob.ec/PLATAFORMA"
DEFAULT_TIMEOUT_SECONDS = 10.0
USER_AGENT = "public-intelligence"

_SEARCH_ENDPOINT = "/api/search_ocds"
_RECORD_ENDPOINT = "/api/record"

ModelT = TypeVar("ModelT", bound=BaseModel)


class SercopClient:
    """Source-specific async client for targeted SERCOP operations."""

    def __init__(
        self,
        *,
        base_url: str = SERCOP_BASE_URL,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        transport: httpx2.AsyncBaseTransport | None = None,
    ) -> None:
        self._client = httpx2.AsyncClient(
            base_url=base_url.rstrip("/"),
            headers={"User-Agent": USER_AGENT},
            timeout=timeout_seconds,
            transport=transport,
        )

    async def __aenter__(self) -> "SercopClient":
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

    async def search(
        self,
        *,
        year: int,
        search: str,
        page: int = 1,
        buyer: str | None = None,
        supplier: str | None = None,
    ) -> Result[SercopSearchPage]:
        """Retrieve one explicit page of source-specific search summaries."""
        self._validate_integer("year", year)
        self._validate_integer("page", page)
        if page < 1:
            raise ValueError("page must be greater than or equal to 1")
        if not isinstance(search, str):
            raise TypeError("search must be a string")
        if len(search.strip()) < 3:
            raise ValueError("search must contain at least three characters")
        self._validate_optional_string("buyer", buyer)
        self._validate_optional_string("supplier", supplier)

        parameters: dict[str, RequestParameter] = {
            "year": year,
            "search": search,
            "page": page,
        }
        if buyer is not None:
            parameters["buyer"] = buyer
        if supplier is not None:
            parameters["supplier"] = supplier

        return await self._request(
            endpoint=_SEARCH_ENDPOINT,
            parameters=parameters,
            mechanism="keyword_search",
            model_type=SercopSearchPage,
        )

    async def get_record(self, *, ocid: str) -> Result[SercopRecordPackage]:
        """Retrieve the current source snapshot for an exact OCID."""
        if not isinstance(ocid, str):
            raise TypeError("ocid must be a string")
        if not ocid.strip():
            raise ValueError("ocid must not be blank")

        return await self._request(
            endpoint=_RECORD_ENDPOINT,
            parameters={"ocid": ocid},
            mechanism="ocid_record",
            model_type=SercopRecordPackage,
            not_found_ocid=ocid,
        )

    async def _request(
        self,
        *,
        endpoint: str,
        parameters: Mapping[str, RequestParameter],
        mechanism: SercopAccessMechanism,
        model_type: type[ModelT],
        not_found_ocid: str | None = None,
    ) -> Result[ModelT]:
        try:
            response = await self._client.get(endpoint, params=parameters)
        except httpx2.RequestError as error:
            raise SercopTransportError(
                endpoint=endpoint,
                reason=str(error) or error.__class__.__name__,
            ) from error

        raw_body = response.content
        content_type = response.headers.get("content-type", "")

        if response.status_code == 404 and not_found_ocid is not None:
            raise SercopNotFoundError(
                ocid=not_found_ocid,
                endpoint=endpoint,
                status_code=response.status_code,
            )
        if not 200 <= response.status_code < 300:
            raise SercopResponseError(
                endpoint=endpoint,
                status_code=response.status_code,
                content_type=content_type or None,
                reason="unexpected HTTP status",
            )

        media_type = content_type.partition(";")[0].strip().lower()
        if media_type != "application/json":
            raise SercopResponseError(
                endpoint=endpoint,
                status_code=response.status_code,
                content_type=content_type or None,
                reason="unexpected successful content type",
            )

        try:
            data = model_type.model_validate_json(raw_body)
        except ValidationError as error:
            raise SercopResponseError(
                endpoint=endpoint,
                status_code=response.status_code,
                content_type=content_type,
                reason="malformed JSON or invalid source envelope",
            ) from error

        provenance = SercopProvenance(
            source_key="sercop",
            access_mechanism=mechanism,
            endpoint=endpoint,
            request_parameters=MappingProxyType(dict(parameters)),
            retrieved_at=datetime.now(UTC),
            http_status=response.status_code,
            content_type=content_type,
            payload_sha256=sha256(raw_body).hexdigest(),
            payload_size=len(raw_body),
            last_modified=response.headers.get("last-modified"),
            etag=response.headers.get("etag"),
        )
        return Result(data=data, raw_body=raw_body, provenance=provenance)

    @staticmethod
    def _validate_integer(name: str, value: object) -> None:
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError(f"{name} must be an integer")

    @staticmethod
    def _validate_optional_string(name: str, value: object | None) -> None:
        if value is not None and not isinstance(value, str):
            raise TypeError(f"{name} must be a string when provided")
