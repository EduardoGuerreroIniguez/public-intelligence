import asyncio
from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from hashlib import sha256
from uuid import UUID, uuid4

import psycopg
import pytest
from psycopg import errors

from public_intelligence.domain.procurement import (
    Award,
    Contract,
    Money,
    OrganizationRef,
    ProcurementProcedure,
    ProcurementRecord,
    SourceReference,
)
from public_intelligence.persistence import (
    PostgresDatabase,
    ProcurementRepository,
    RawEvidenceInput,
    RawEvidenceRepository,
)

BUYER = OrganizationRef(external_id=None, name="Example public buyer")
SUPPLIER_ONE = OrganizationRef(external_id="supplier-1", name="Supplier One")
SUPPLIER_TWO = OrganizationRef(external_id=None, name=None)
PRECISE_AMOUNT = Decimal("12345678901234567890.12345678901234567890")


@pytest.fixture
def procurement_repository(database: PostgresDatabase) -> ProcurementRepository:
    return ProcurementRepository(database)


@pytest.mark.anyio
async def test_full_domain_round_trip_is_source_independent(
    procurement_repository: ProcurementRepository,
    repository: RawEvidenceRepository,
) -> None:
    evidence_id = await _save_evidence(repository, "round-trip")
    record = _full_record(evidence_id=evidence_id)

    saved = await procurement_repository.save(record)
    loaded = await procurement_repository.get(
        source=record.source_reference.source,
        external_id=record.source_reference.external_id,
    )

    assert saved.id.version == 4
    assert saved.record == record
    assert loaded == saved
    assert loaded.record.procedure is not None
    assert loaded.record.procedure.value is not None
    assert loaded.record.procedure.value.amount == PRECISE_AMOUNT
    assert isinstance(loaded.record.procedure.value.amount, Decimal)


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("suffix", "suppliers", "awards", "contracts"),
    [
        ("absent", None, None, None),
        ("empty", (), (), ()),
    ],
)
async def test_collection_absence_and_empty_state_round_trip(
    procurement_repository: ProcurementRepository,
    suffix: str,
    suppliers: tuple[OrganizationRef, ...] | None,
    awards: tuple[Award, ...] | None,
    contracts: tuple[Contract, ...] | None,
) -> None:
    record = ProcurementRecord(
        source_reference=SourceReference(
            source="example_source",
            external_id=f"collections-{suffix}",
        ),
        buyer=None,
        suppliers=suppliers,
        procedure=None,
        awards=awards,
        contracts=contracts,
    )

    await procurement_repository.save(record)
    loaded = await procurement_repository.get(
        source="example_source",
        external_id=f"collections-{suffix}",
    )

    assert loaded is not None
    assert loaded.record == record


@pytest.mark.anyio
@pytest.mark.parametrize("award_suppliers", [None, ()])
async def test_award_supplier_absence_and_empty_state_round_trip(
    procurement_repository: ProcurementRepository,
    award_suppliers: tuple[OrganizationRef, ...] | None,
) -> None:
    award = Award(
        external_id="award",
        status=None,
        date=None,
        value=None,
        suppliers=award_suppliers,
    )
    record = _minimal_record(
        external_id=f"award-suppliers-{award_suppliers is not None}",
        awards=(award,),
    )

    await procurement_repository.save(record)
    loaded = await procurement_repository.get(
        source="example_source",
        external_id=record.source_reference.external_id,
    )

    assert loaded is not None
    assert loaded.record.awards is not None
    assert loaded.record.awards[0].suppliers == award_suppliers


@pytest.mark.anyio
async def test_nullable_organization_fields_round_trip(
    procurement_repository: ProcurementRepository,
) -> None:
    empty_reference = OrganizationRef(external_id=None, name=None)
    award = Award(
        external_id="award-null-organization",
        status=None,
        date=None,
        value=None,
        suppliers=(empty_reference,),
    )
    record = ProcurementRecord(
        source_reference=SourceReference(
            source="example_source",
            external_id="nullable-organizations",
        ),
        buyer=empty_reference,
        suppliers=(empty_reference,),
        procedure=None,
        awards=(award,),
        contracts=None,
    )

    await procurement_repository.save(record)
    loaded = await procurement_repository.get(
        source="example_source",
        external_id="nullable-organizations",
    )

    assert loaded is not None
    assert loaded.record == record


@pytest.mark.anyio
async def test_money_precision_zero_missing_and_nullable_currency_round_trip(
    procurement_repository: ProcurementRepository,
) -> None:
    record = _full_record(evidence_id=None, external_id="money")

    await procurement_repository.save(record)
    loaded = await procurement_repository.get(
        source="example_source",
        external_id="money",
    )

    assert loaded is not None
    assert loaded.record.procedure is not None
    assert loaded.record.procedure.value == Money(
        amount=PRECISE_AMOUNT,
        currency=None,
    )
    assert loaded.record.awards is not None
    assert loaded.record.awards[0].value == Money(
        amount=Decimal("0"),
        currency=None,
    )
    assert loaded.record.awards[1].value is None


@pytest.mark.anyio
async def test_identical_save_preserves_id_and_refreshes_reprocessing_time(
    procurement_repository: ProcurementRepository,
    database: PostgresDatabase,
) -> None:
    record = _full_record(evidence_id=None, external_id="reprocessed")
    first = await procurement_repository.save(record)
    async with database.connection() as connection:
        await connection.execute(
            """
            UPDATE procurements
            SET updated_at = TIMESTAMPTZ '2000-01-01 00:00:00+00'
            WHERE id = %(id)s
            """,
            {"id": first.id},
        )

    second = await procurement_repository.save(record)
    counts = await _normalized_counts(database, first.id)

    assert second.id == first.id
    assert second.created_at == first.created_at
    assert second.updated_at > datetime(2000, 1, 1, tzinfo=UTC)
    assert second.updated_at != datetime(2000, 1, 1, tzinfo=UTC)
    assert counts == {
        "procurements": 1,
        "suppliers": 2,
        "awards": 2,
        "award_suppliers": 2,
        "contracts": 1,
    }


@pytest.mark.anyio
async def test_changed_snapshot_replaces_stale_children_and_evidence(
    procurement_repository: ProcurementRepository,
    repository: RawEvidenceRepository,
    database: PostgresDatabase,
) -> None:
    first_evidence = await _save_evidence(repository, "first")
    second_evidence = await _save_evidence(repository, "second")
    first_record = _full_record(evidence_id=first_evidence, external_id="changed")
    first = await procurement_repository.save(first_record)
    assert first_record.procedure is not None
    changed = replace(
        first_record,
        source_reference=replace(
            first_record.source_reference,
            evidence_id=second_evidence,
        ),
        buyer=OrganizationRef(external_id="new-buyer", name="New Buyer"),
        suppliers=(OrganizationRef(external_id="new", name="New Supplier"),),
        procedure=replace(
            first_record.procedure,
            title="Changed title",
            value=Money(amount=Decimal("0"), currency="USD"),
        ),
        awards=(),
        contracts=None,
    )

    second = await procurement_repository.save(changed)
    loaded = await procurement_repository.get(
        source="example_source",
        external_id="changed",
    )

    assert second.id == first.id
    assert second.created_at == first.created_at
    assert loaded is not None
    assert loaded.record == changed
    assert loaded.record.source_reference.evidence_id == second_evidence
    assert await _normalized_counts(database, first.id) == {
        "procurements": 1,
        "suppliers": 1,
        "awards": 0,
        "award_suppliers": 0,
        "contracts": 0,
    }


@pytest.mark.anyio
async def test_nullable_and_invalid_evidence_foreign_keys(
    procurement_repository: ProcurementRepository,
    database: PostgresDatabase,
) -> None:
    without_evidence = _minimal_record(external_id="without-evidence")
    saved = await procurement_repository.save(without_evidence)
    assert saved.record.source_reference.evidence_id is None

    invalid = _minimal_record(
        external_id="invalid-evidence",
        evidence_id=uuid4(),
    )
    with pytest.raises(errors.ForeignKeyViolation):
        await procurement_repository.save(invalid)

    assert (
        await procurement_repository.get(
            source="example_source",
            external_id="invalid-evidence",
        )
        is None
    )
    assert await _table_count(database, "procurements") == 1


@pytest.mark.anyio
async def test_referenced_raw_evidence_delete_is_restricted(
    procurement_repository: ProcurementRepository,
    repository: RawEvidenceRepository,
    database: PostgresDatabase,
) -> None:
    evidence_id = await _save_evidence(repository, "restricted")
    await procurement_repository.save(
        _minimal_record(external_id="restricted", evidence_id=evidence_id)
    )

    with pytest.raises(errors.RestrictViolation):
        async with database.connection() as connection:
            await connection.execute(
                "DELETE FROM raw_evidence WHERE id = %(id)s",
                {"id": evidence_id},
            )

    assert await repository.get(evidence_id) is not None


@pytest.mark.anyio
async def test_child_failure_rolls_back_complete_previous_snapshot(
    procurement_repository: ProcurementRepository,
) -> None:
    original = _full_record(evidence_id=None, external_id="rollback")
    before = await procurement_repository.save(original)
    invalid = replace(
        original,
        buyer=OrganizationRef(external_id="changed", name="Changed buyer"),
        suppliers=(OrganizationRef(external_id="invalid", name="contains\x00nul"),),
        awards=(),
        contracts=(),
    )

    with pytest.raises(psycopg.DataError):
        await procurement_repository.save(invalid)

    after = await procurement_repository.get(
        source="example_source",
        external_id="rollback",
    )
    assert after == before


@pytest.mark.anyio
async def test_get_holds_one_transaction_and_blocks_concurrent_replacement(
    procurement_repository: ProcurementRepository,
    database: PostgresDatabase,
) -> None:
    original = _full_record(evidence_id=None, external_id="concurrent")
    await procurement_repository.save(original)
    changed = replace(
        original,
        buyer=OrganizationRef(external_id="changed", name="Changed buyer"),
        suppliers=(OrganizationRef(external_id="changed", name="Changed"),),
    )

    async with database.connection() as blocker:
        await blocker.execute(
            "LOCK TABLE procurement_suppliers IN ACCESS EXCLUSIVE MODE"
        )
        get_task = asyncio.create_task(
            procurement_repository.get(
                source="example_source",
                external_id="concurrent",
            )
        )
        await _wait_for_pending_locks(database, minimum=1)
        save_task = asyncio.create_task(procurement_repository.save(changed))
        await _wait_for_pending_locks(database, minimum=2)
        assert not get_task.done()
        assert not save_task.done()

    read_during_replacement, saved = await asyncio.gather(get_task, save_task)
    final = await procurement_repository.get(
        source="example_source",
        external_id="concurrent",
    )

    assert read_during_replacement is not None
    assert read_during_replacement.record == original
    assert saved.record == changed
    assert final is not None
    assert final.record == changed


@pytest.mark.anyio
async def test_get_unknown_identity_returns_none(
    procurement_repository: ProcurementRepository,
) -> None:
    assert (
        await procurement_repository.get(
            source="example_source",
            external_id="unknown",
        )
        is None
    )


def _full_record(
    *,
    evidence_id: UUID | None,
    external_id: str = "process-1",
) -> ProcurementRecord:
    procedure = ProcurementProcedure(
        external_id="procedure-1",
        title="Example procedure",
        description="Factual description",
        status="active",
        method="direct",
        method_details="Source method details",
        category="services",
        value=Money(amount=PRECISE_AMOUNT, currency=None),
    )
    awards = (
        Award(
            external_id="award-1",
            status=None,
            date=datetime(2026, 8, 21, 12, 0, tzinfo=UTC),
            value=Money(amount=Decimal("0"), currency=None),
            suppliers=(SUPPLIER_TWO, SUPPLIER_ONE),
        ),
        Award(
            external_id="award-2",
            status="active",
            date=None,
            value=None,
            suppliers=None,
        ),
    )
    contracts = (
        Contract(
            external_id="contract-1",
            award_external_id="award-1",
            status="active",
            date_signed=datetime(2026, 8, 22, 9, 30, tzinfo=UTC),
            value=Money(amount=Decimal("99.9900"), currency="USD"),
        ),
    )
    return ProcurementRecord(
        source_reference=SourceReference(
            source="example_source",
            external_id=external_id,
            evidence_id=evidence_id,
        ),
        buyer=BUYER,
        suppliers=(SUPPLIER_ONE, SUPPLIER_TWO),
        procedure=procedure,
        awards=awards,
        contracts=contracts,
    )


def _minimal_record(
    *,
    external_id: str,
    evidence_id: UUID | None = None,
    awards: tuple[Award, ...] | None = None,
) -> ProcurementRecord:
    return ProcurementRecord(
        source_reference=SourceReference(
            source="example_source",
            external_id=external_id,
            evidence_id=evidence_id,
        ),
        buyer=None,
        suppliers=None,
        procedure=None,
        awards=awards,
        contracts=None,
    )


async def _save_evidence(repository: RawEvidenceRepository, suffix: str) -> UUID:
    payload = f'{{"evidence":"{suffix}"}}'.encode()
    stored = await repository.save(
        RawEvidenceInput(
            source="example_source",
            mechanism="fixture",
            source_key=suffix,
            endpoint=f"/fixtures/{suffix}",
            parameters={"fixture": suffix},
            retrieved_at=datetime(2026, 8, 22, tzinfo=UTC),
            http_status=200,
            content_type="application/json",
            payload_sha256=sha256(payload).hexdigest(),
            payload_byte_size=len(payload),
            payload=payload,
        )
    )
    return stored.id


async def _normalized_counts(
    database: PostgresDatabase,
    procurement_id: UUID,
) -> dict[str, int]:
    async with database.connection() as connection:
        row = await (
            await connection.execute(
                """
                SELECT
                    (SELECT count(*) FROM procurements WHERE id = %(id)s)
                        AS procurements,
                    (SELECT count(*) FROM procurement_suppliers
                        WHERE procurement_id = %(id)s) AS suppliers,
                    (SELECT count(*) FROM procurement_awards
                        WHERE procurement_id = %(id)s) AS awards,
                    (SELECT count(*) FROM award_suppliers
                        WHERE procurement_id = %(id)s) AS award_suppliers,
                    (SELECT count(*) FROM procurement_contracts
                        WHERE procurement_id = %(id)s) AS contracts
                """,
                {"id": procurement_id},
            )
        ).fetchone()
    assert row is not None
    return dict(row)


async def _table_count(database: PostgresDatabase, table_name: str) -> int:
    if table_name != "procurements":
        raise ValueError("unsupported test table")
    async with database.connection() as connection:
        row = await (
            await connection.execute("SELECT count(*) AS count FROM procurements")
        ).fetchone()
    assert row is not None
    return row["count"]


async def _wait_for_pending_locks(
    database: PostgresDatabase,
    *,
    minimum: int,
) -> None:
    for _ in range(100):
        async with database.connection() as connection:
            row = await (
                await connection.execute(
                    """
                    SELECT count(*) AS count
                    FROM pg_locks locks
                    JOIN pg_stat_activity activity ON activity.pid = locks.pid
                    WHERE activity.datname = current_database()
                      AND NOT locks.granted
                    """
                )
            ).fetchone()
        assert row is not None
        if row["count"] >= minimum:
            return
        await asyncio.sleep(0.01)
    raise AssertionError(f"expected at least {minimum} pending PostgreSQL locks")
