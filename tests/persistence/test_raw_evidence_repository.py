from collections.abc import Mapping
from dataclasses import replace
from datetime import UTC, datetime, timedelta, timezone
from hashlib import sha256
from uuid import uuid4

import pytest

from public_intelligence.persistence import (
    PostgresDatabase,
    RawEvidenceInput,
    RawEvidenceIntegrityError,
    RawEvidenceRepository,
)


def evidence_input(
    payload: bytes = b'{"source":"example"}\n',
    *,
    source: str = "example_source",
    parameters: Mapping[str, object] | None = None,
    retrieved_at: datetime | None = None,
) -> RawEvidenceInput:
    return RawEvidenceInput(
        source=source,
        mechanism="targeted_lookup",
        source_key="external-123",
        endpoint="/records/123",
        parameters=parameters or {"record": "123", "page": 1},
        retrieved_at=retrieved_at or datetime(2026, 8, 19, 12, 0, tzinfo=UTC),
        http_status=200,
        content_type="application/json",
        payload_sha256=sha256(payload).hexdigest(),
        payload_byte_size=len(payload),
        payload=payload,
        etag='"example-etag"',
        last_modified="Wed, 19 Aug 2026 12:00:00 GMT",
    )


@pytest.mark.anyio
async def test_save_and_get_round_trip_all_fields(
    repository: RawEvidenceRepository,
) -> None:
    input_evidence = evidence_input(
        parameters={
            "record": "123",
            "page": 1,
            "active": True,
            "optional": None,
            "filters": ["water", "health"],
            "nested": {"limit": 10},
        }
    )

    saved = await repository.save(input_evidence)
    loaded = await repository.get(saved.id)

    assert saved.id.version == 4
    assert loaded == saved
    assert saved.source == input_evidence.source
    assert saved.mechanism == input_evidence.mechanism
    assert saved.source_key == input_evidence.source_key
    assert saved.endpoint == input_evidence.endpoint
    assert saved.parameters == input_evidence.parameters
    assert saved.retrieved_at == input_evidence.retrieved_at
    assert saved.http_status == input_evidence.http_status
    assert saved.content_type == input_evidence.content_type
    assert saved.payload_sha256 == input_evidence.payload_sha256
    assert saved.payload_byte_size == input_evidence.payload_byte_size
    assert saved.payload == input_evidence.payload
    assert saved.etag == input_evidence.etag
    assert saved.last_modified == input_evidence.last_modified
    assert saved.created_at.utcoffset() == timedelta(0)


@pytest.mark.anyio
async def test_get_unknown_id_returns_none(
    repository: RawEvidenceRepository,
) -> None:
    assert await repository.get(uuid4()) is None


@pytest.mark.anyio
@pytest.mark.parametrize(
    "payload",
    [
        "Información pública ñ".encode(),
        b"binary\x00payload",
        b'{"a":1, "b":2}',
        b'{\n  "a": 1\n}\n',
    ],
)
async def test_payload_bytes_round_trip_exactly(
    repository: RawEvidenceRepository,
    payload: bytes,
) -> None:
    saved = await repository.save(evidence_input(payload))
    loaded = await repository.get(saved.id)

    assert loaded is not None
    assert loaded.payload == payload
    assert loaded.payload_sha256 == sha256(payload).hexdigest()
    assert loaded.payload_byte_size == len(payload)


@pytest.mark.anyio
@pytest.mark.parametrize(
    "invalid_input",
    [
        replace(evidence_input(), payload_sha256="0" * 64),
        replace(evidence_input(), payload_byte_size=999),
    ],
)
async def test_invalid_integrity_metadata_is_rejected_without_insert(
    repository: RawEvidenceRepository,
    database: PostgresDatabase,
    invalid_input: RawEvidenceInput,
) -> None:
    with pytest.raises(RawEvidenceIntegrityError):
        await repository.save(invalid_input)

    async with database.connection() as connection:
        row = await (
            await connection.execute("SELECT count(*) AS count FROM raw_evidence")
        ).fetchone()
    assert row == {"count": 0}


@pytest.mark.anyio
async def test_naive_retrieval_timestamp_is_rejected(
    repository: RawEvidenceRepository,
) -> None:
    input_evidence = evidence_input(retrieved_at=datetime(2026, 8, 19, 12, 0))

    with pytest.raises(ValueError, match="timezone-aware"):
        await repository.save(input_evidence)


@pytest.mark.anyio
async def test_offset_timestamp_is_returned_in_utc(
    repository: RawEvidenceRepository,
) -> None:
    offset = timezone(timedelta(hours=-5))
    input_evidence = evidence_input(
        retrieved_at=datetime(2026, 8, 19, 7, 0, tzinfo=offset)
    )

    saved = await repository.save(input_evidence)

    assert saved.retrieved_at == datetime(2026, 8, 19, 12, 0, tzinfo=UTC)
    assert saved.retrieved_at.utcoffset() == timedelta(0)


@pytest.mark.anyio
async def test_duplicate_payload_observations_are_independent(
    repository: RawEvidenceRepository,
) -> None:
    first_input = evidence_input()
    second_input = replace(
        first_input,
        retrieved_at=first_input.retrieved_at + timedelta(minutes=5),
    )

    first = await repository.save(first_input)
    second = await repository.save(second_input)

    assert first.id != second.id
    assert first.payload == second.payload
    assert await repository.get(first.id) == first
    assert await repository.get(second.id) == second


@pytest.mark.anyio
async def test_save_many_uses_the_same_source_neutral_insert_semantics(
    repository: RawEvidenceRepository,
) -> None:
    first = evidence_input(b'{"source":"first"}')
    second = evidence_input(
        b'{"source":"second"}',
        source="another_source",
        parameters={"partition": "bounded"},
    )

    stored = await repository.save_many((first, second))

    assert len(stored) == 2
    assert stored[0].source == "example_source"
    assert stored[0].payload == first.payload
    assert stored[1].source == "another_source"
    assert stored[1].parameters == {"partition": "bounded"}
    assert await repository.get(stored[0].id) == stored[0]
    assert await repository.get(stored[1].id) == stored[1]


@pytest.mark.anyio
async def test_save_many_validates_every_payload_before_inserting(
    repository: RawEvidenceRepository,
    database: PostgresDatabase,
) -> None:
    invalid = replace(evidence_input(), payload_sha256="0" * 64)

    with pytest.raises(RawEvidenceIntegrityError):
        await repository.save_many((evidence_input(), invalid))

    async with database.connection() as connection:
        row = await (
            await connection.execute("SELECT count(*) AS count FROM raw_evidence")
        ).fetchone()
    assert row == {"count": 0}


@pytest.mark.anyio
async def test_save_many_rolls_back_the_group_on_database_failure(
    repository: RawEvidenceRepository,
    database: PostgresDatabase,
) -> None:
    invalid_parameters = replace(
        evidence_input(b'{"source":"second"}'),
        parameters={"not_json": object()},
    )

    with pytest.raises(TypeError, match="JSON serializable"):
        await repository.save_many((evidence_input(), invalid_parameters))

    async with database.connection() as connection:
        row = await (
            await connection.execute("SELECT count(*) AS count FROM raw_evidence")
        ).fetchone()
    assert row == {"count": 0}
