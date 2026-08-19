"""PostgreSQL repository for source-neutral raw evidence."""

from collections.abc import Mapping
from datetime import UTC
from hashlib import sha256
from hmac import compare_digest
from typing import Any
from uuid import UUID, uuid4

from psycopg.types.json import Jsonb

from ..database import PostgresDatabase
from .models import RawEvidence, RawEvidenceInput

_COLUMNS = """
    id,
    source,
    mechanism,
    source_key,
    endpoint,
    parameters,
    retrieved_at,
    http_status,
    content_type,
    payload_sha256,
    payload_byte_size,
    payload,
    etag,
    last_modified,
    created_at
"""

_INSERT = f"""
    INSERT INTO raw_evidence (
        id,
        source,
        mechanism,
        source_key,
        endpoint,
        parameters,
        retrieved_at,
        http_status,
        content_type,
        payload_sha256,
        payload_byte_size,
        payload,
        etag,
        last_modified
    ) VALUES (
        %(id)s,
        %(source)s,
        %(mechanism)s,
        %(source_key)s,
        %(endpoint)s,
        %(parameters)s,
        %(retrieved_at)s,
        %(http_status)s,
        %(content_type)s,
        %(payload_sha256)s,
        %(payload_byte_size)s,
        %(payload)s,
        %(etag)s,
        %(last_modified)s
    )
    RETURNING {_COLUMNS}
"""

_GET = f"""
    SELECT {_COLUMNS}
    FROM raw_evidence
    WHERE id = %(id)s
"""


class RawEvidenceIntegrityError(ValueError):
    """Declared payload integrity metadata does not match the exact bytes."""


class RawEvidenceRepository:
    """Store and retrieve raw source observations without interpretation."""

    def __init__(self, database: PostgresDatabase) -> None:
        self._database = database

    async def save(self, evidence: RawEvidenceInput) -> RawEvidence:
        """Validate and store one independent raw evidence observation."""
        self._validate(evidence)
        retrieved_at = evidence.retrieved_at.astimezone(UTC)
        evidence_id = uuid4()
        parameters: Mapping[str, object] = {
            "id": evidence_id,
            "source": evidence.source,
            "mechanism": evidence.mechanism,
            "source_key": evidence.source_key,
            "endpoint": evidence.endpoint,
            "parameters": Jsonb(dict(evidence.parameters)),
            "retrieved_at": retrieved_at,
            "http_status": evidence.http_status,
            "content_type": evidence.content_type,
            "payload_sha256": evidence.payload_sha256,
            "payload_byte_size": evidence.payload_byte_size,
            "payload": evidence.payload,
            "etag": evidence.etag,
            "last_modified": evidence.last_modified,
        }

        async with self._database.connection() as connection:
            cursor = await connection.execute(_INSERT, parameters)
            row = await cursor.fetchone()

        if row is None:  # pragma: no cover - PostgreSQL RETURNING contract
            raise RuntimeError("PostgreSQL did not return the inserted raw evidence")
        return self._from_row(row)

    async def get(self, evidence_id: UUID) -> RawEvidence | None:
        """Retrieve one observation by its internal identifier."""
        async with self._database.connection() as connection:
            cursor = await connection.execute(_GET, {"id": evidence_id})
            row = await cursor.fetchone()

        if row is None:
            return None
        return self._from_row(row)

    @staticmethod
    def _validate(evidence: RawEvidenceInput) -> None:
        if not isinstance(evidence.payload, bytes):
            raise TypeError("payload must be bytes")
        actual_sha256 = sha256(evidence.payload).hexdigest()
        if not compare_digest(actual_sha256, evidence.payload_sha256.lower()):
            raise RawEvidenceIntegrityError(
                "declared payload SHA-256 does not match payload bytes"
            )
        if len(evidence.payload) != evidence.payload_byte_size:
            raise RawEvidenceIntegrityError(
                "declared payload byte size does not match payload bytes"
            )
        if (
            evidence.retrieved_at.tzinfo is None
            or evidence.retrieved_at.utcoffset() is None
        ):
            raise ValueError("retrieved_at must be timezone-aware")

    @staticmethod
    def _from_row(row: Mapping[str, Any]) -> RawEvidence:
        return RawEvidence(
            id=row["id"],
            source=row["source"],
            mechanism=row["mechanism"],
            source_key=row["source_key"],
            endpoint=row["endpoint"],
            parameters=row["parameters"],
            retrieved_at=row["retrieved_at"],
            http_status=row["http_status"],
            content_type=row["content_type"],
            payload_sha256=row["payload_sha256"],
            payload_byte_size=row["payload_byte_size"],
            payload=bytes(row["payload"]),
            etag=row["etag"],
            last_modified=row["last_modified"],
            created_at=row["created_at"],
        )
