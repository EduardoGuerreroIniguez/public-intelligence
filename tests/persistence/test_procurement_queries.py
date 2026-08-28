from dataclasses import FrozenInstanceError
from datetime import UTC
from decimal import Decimal

import pytest

from public_intelligence.domain.procurement import (
    Award,
    Money,
    OrganizationRef,
    ProcurementProcedure,
    ProcurementRecord,
    SourceReference,
)
from public_intelligence.persistence import (
    PostgresDatabase,
    ProcurementQueries,
    ProcurementRepository,
    ProcurementSearch,
)


@pytest.mark.parametrize("field", ["buyer", "supplier", "status", "currency"])
@pytest.mark.parametrize("value", ["", "   "])
def test_search_rejects_blank_text_filters(field: str, value: str) -> None:
    with pytest.raises(ValueError, match=field):
        ProcurementSearch(**{field: value})  # type: ignore[arg-type]


def test_search_preserves_nonblank_text_exactly_as_supplied() -> None:
    search = ProcurementSearch(
        buyer=" Buyer ",
        supplier=" Supplier ",
        status=" Active ",
        currency=" usd ",
    )

    assert search.buyer == " Buyer "
    assert search.supplier == " Supplier "
    assert search.status == " Active "
    assert search.currency == " usd "

    with pytest.raises(FrozenInstanceError):
        search.limit = 1  # type: ignore[misc]


@pytest.mark.parametrize("field", ["buyer", "supplier", "status", "currency"])
def test_search_rejects_non_string_text_filters(field: str) -> None:
    with pytest.raises(TypeError, match=field):
        ProcurementSearch(**{field: 1})  # type: ignore[arg-type]


@pytest.mark.parametrize("field", ["min_value", "max_value"])
def test_search_requires_finite_decimal_values(field: str) -> None:
    with pytest.raises(TypeError, match=field):
        ProcurementSearch(currency="USD", **{field: 1.5})  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="finite"):
        ProcurementSearch(currency="USD", **{field: Decimal("NaN")})  # type: ignore[arg-type]


def test_search_validates_value_range_and_currency() -> None:
    with pytest.raises(ValueError, match="currency"):
        ProcurementSearch(min_value=Decimal("1"))
    with pytest.raises(ValueError, match="min_value"):
        ProcurementSearch(
            currency="USD",
            min_value=Decimal("2"),
            max_value=Decimal("1"),
        )


@pytest.mark.parametrize(
    ("values", "error_type"),
    [
        ({"limit": True}, TypeError),
        ({"limit": 0}, ValueError),
        ({"limit": 201}, ValueError),
        ({"offset": False}, TypeError),
        ({"offset": -1}, ValueError),
    ],
)
def test_search_validates_bounded_pagination(
    values: dict[str, object],
    error_type: type[Exception],
) -> None:
    with pytest.raises(error_type):
        ProcurementSearch(**values)  # type: ignore[arg-type]


@pytest.mark.anyio
async def test_search_projects_orders_and_paginates_with_total(
    database: PostgresDatabase,
) -> None:
    repository = ProcurementRepository(database)
    for record in [
        _record(source="sercop", external_id="b"),
        _record(source="sercop", external_id="a"),
        _record(source="example_source", external_id="z"),
        _record(source="example_source", external_id="newest"),
    ]:
        await repository.save(record)

    async with database.connection() as connection:
        await connection.execute(
            """
            UPDATE procurements
            SET updated_at = CASE
                WHEN external_id = 'newest'
                    THEN TIMESTAMPTZ '2026-08-29 00:00:00+00'
                ELSE TIMESTAMPTZ '2026-08-28 00:00:00+00'
            END
            """
        )

    queries = ProcurementQueries(database)
    first = await queries.search(ProcurementSearch(limit=2))
    second = await queries.search(ProcurementSearch(limit=2, offset=2))
    beyond = await queries.search(ProcurementSearch(limit=2, offset=10))

    assert first.total == second.total == beyond.total == 4
    assert first.limit == 2
    assert first.offset == 0
    assert [(item.source, item.external_id) for item in first.items] == [
        ("example_source", "newest"),
        ("example_source", "z"),
    ]
    assert [(item.source, item.external_id) for item in second.items] == [
        ("sercop", "a"),
        ("sercop", "b"),
    ]
    assert beyond.items == ()
    assert all(item.updated_at.tzinfo == UTC for item in first.items + second.items)


@pytest.mark.anyio
async def test_buyer_search_is_case_insensitive_literal_substring(
    database: PostgresDatabase,
) -> None:
    repository = ProcurementRepository(database)
    await repository.save(
        _record(
            external_id="literal",
            buyer_name=r"Authority 100%_Done\North",
        )
    )
    await repository.save(
        _record(
            external_id="wildcard-lookalike",
            buyer_name="Authority 100xxDoneNorth",
        )
    )

    page = await ProcurementQueries(database).search(
        ProcurementSearch(buyer=r"100%_done\N")
    )

    assert [item.external_id for item in page.items] == ["literal"]
    assert page.total == 1


@pytest.mark.anyio
async def test_supplier_search_uses_procurement_suppliers_without_duplicates(
    database: PostgresDatabase,
) -> None:
    repository = ProcurementRepository(database)
    matching = _record(
        external_id="procurement-suppliers",
        suppliers=(
            OrganizationRef(external_id="one", name="Needle 100%_Supplier"),
            OrganizationRef(external_id="two", name="Another needle 100%_supplier"),
        ),
    )
    award_only = _record(
        external_id="award-only",
        suppliers=None,
        awards=(
            Award(
                external_id="award",
                status=None,
                date=None,
                value=None,
                suppliers=(
                    OrganizationRef(
                        external_id="award-supplier",
                        name="Needle 100%_Supplier",
                    ),
                ),
            ),
        ),
    )
    lookalike = _record(
        external_id="wildcard-lookalike",
        suppliers=(OrganizationRef(external_id="three", name="Needle 100xxSupplier"),),
    )
    for record in (matching, award_only, lookalike):
        await repository.save(record)

    page = await ProcurementQueries(database).search(
        ProcurementSearch(supplier="NEEDLE 100%_supplier")
    )

    assert [item.external_id for item in page.items] == ["procurement-suppliers"]
    assert page.total == 1


@pytest.mark.anyio
async def test_status_is_exact_case_sensitive_and_filters_combine_with_and(
    database: PostgresDatabase,
) -> None:
    repository = ProcurementRepository(database)
    for record in [
        _record(
            external_id="match",
            buyer_name="Municipio Central",
            status="complete",
        ),
        _record(
            external_id="wrong-case",
            buyer_name="Municipio Central",
            status="Complete",
        ),
        _record(external_id="wrong-buyer", buyer_name="Other", status="complete"),
    ]:
        await repository.save(record)

    page = await ProcurementQueries(database).search(
        ProcurementSearch(buyer="municipio", status="complete")
    )

    assert [item.external_id for item in page.items] == ["match"]


@pytest.mark.anyio
async def test_decimal_ranges_are_inclusive_and_require_exact_currency(
    database: PostgresDatabase,
) -> None:
    repository = ProcurementRepository(database)
    for record in [
        _record(external_id="usd-10", amount=Decimal("10.000"), currency="USD"),
        _record(external_id="usd-20", amount=Decimal("20.000"), currency="USD"),
        _record(external_id="eur-15", amount=Decimal("15"), currency="EUR"),
        _record(external_id="lower-usd", amount=Decimal("15"), currency="usd"),
        _record(external_id="unknown", amount=Decimal("15"), currency=None),
        _record(external_id="missing", amount=None, currency=None),
    ]:
        await repository.save(record)

    queries = ProcurementQueries(database)
    ranged = await queries.search(
        ProcurementSearch(
            currency="USD",
            min_value=Decimal("10"),
            max_value=Decimal("20"),
        )
    )
    currency_only = await queries.search(ProcurementSearch(currency="USD"))

    assert {item.external_id for item in ranged.items} == {"usd-10", "usd-20"}
    assert ranged.total == 2
    assert {item.external_id for item in currency_only.items} == {
        "usd-10",
        "usd-20",
    }
    assert all(item.procedure_value is not None for item in ranged.items)
    by_id = {item.external_id: item for item in ranged.items}
    assert by_id["usd-10"].procedure_value == Money(
        amount=Decimal("10.000"),
        currency="USD",
    )


@pytest.mark.anyio
async def test_result_preserves_missing_money_and_explicit_zero(
    database: PostgresDatabase,
) -> None:
    repository = ProcurementRepository(database)
    await repository.save(_record(external_id="missing", amount=None, currency=None))
    await repository.save(
        _record(external_id="zero", amount=Decimal("0"), currency=None)
    )

    page = await ProcurementQueries(database).search(ProcurementSearch())
    by_id = {item.external_id: item for item in page.items}

    assert by_id["missing"].procedure_value is None
    assert by_id["zero"].procedure_value == Money(
        amount=Decimal("0"),
        currency=None,
    )


@pytest.mark.anyio
async def test_full_detail_get_delegates_to_procurement_repository(
    database: PostgresDatabase,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = ProcurementRepository(database)
    stored = await repository.save(_record(external_id="detail"))
    calls: list[tuple[str, str]] = []

    async def fake_get(
        self: ProcurementRepository,
        *,
        source: str,
        external_id: str,
    ) -> object:
        calls.append((source, external_id))
        return stored

    monkeypatch.setattr(ProcurementRepository, "get", fake_get)
    loaded = await ProcurementQueries(database).get(
        source="example_source",
        external_id="detail",
    )

    assert loaded == stored
    assert calls == [("example_source", "detail")]


@pytest.mark.anyio
async def test_full_detail_unknown_identity_returns_none(
    database: PostgresDatabase,
) -> None:
    assert (
        await ProcurementQueries(database).get(
            source="example_source",
            external_id="unknown",
        )
        is None
    )


def _record(
    *,
    external_id: str,
    source: str = "example_source",
    buyer_name: str | None = "Example Buyer",
    suppliers: tuple[OrganizationRef, ...] | None = (),
    awards: tuple[Award, ...] | None = (),
    status: str | None = "active",
    amount: Decimal | None = Decimal("100"),
    currency: str | None = "USD",
) -> ProcurementRecord:
    return ProcurementRecord(
        source_reference=SourceReference(source=source, external_id=external_id),
        buyer=(
            None
            if buyer_name is None
            else OrganizationRef(external_id=None, name=buyer_name)
        ),
        suppliers=suppliers,
        procedure=ProcurementProcedure(
            external_id=f"procedure-{external_id}",
            title=f"Title {external_id}",
            description=None,
            status=status,
            method=None,
            method_details=None,
            category=None,
            value=(None if amount is None else Money(amount=amount, currency=currency)),
        ),
        awards=awards,
        contracts=(),
    )
