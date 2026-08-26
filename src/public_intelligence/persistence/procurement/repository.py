"""PostgreSQL repository for current normalized procurement snapshots."""

from collections.abc import Mapping
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from psycopg import AsyncConnection
from psycopg.rows import DictRow

from public_intelligence.domain.procurement import (
    Award,
    Contract,
    Money,
    OrganizationRef,
    ProcurementProcedure,
    ProcurementRecord,
    SourceReference,
)

from ..database import PostgresDatabase
from .models import StoredProcurement

_UPSERT_PROCUREMENT = """
    INSERT INTO procurements (
        id,
        source,
        external_id,
        evidence_id,
        buyer_present,
        buyer_external_id,
        buyer_name,
        procedure_external_id,
        procedure_title,
        procedure_description,
        procedure_status,
        procedure_method,
        procedure_method_details,
        procedure_category,
        procedure_value_amount,
        procedure_value_currency,
        suppliers_present,
        awards_present,
        contracts_present
    ) VALUES (
        %(id)s,
        %(source)s,
        %(external_id)s,
        %(evidence_id)s,
        %(buyer_present)s,
        %(buyer_external_id)s,
        %(buyer_name)s,
        %(procedure_external_id)s,
        %(procedure_title)s,
        %(procedure_description)s,
        %(procedure_status)s,
        %(procedure_method)s,
        %(procedure_method_details)s,
        %(procedure_category)s,
        %(procedure_value_amount)s,
        %(procedure_value_currency)s,
        %(suppliers_present)s,
        %(awards_present)s,
        %(contracts_present)s
    )
    ON CONFLICT (source, external_id) DO UPDATE SET
        evidence_id = EXCLUDED.evidence_id,
        buyer_present = EXCLUDED.buyer_present,
        buyer_external_id = EXCLUDED.buyer_external_id,
        buyer_name = EXCLUDED.buyer_name,
        procedure_external_id = EXCLUDED.procedure_external_id,
        procedure_title = EXCLUDED.procedure_title,
        procedure_description = EXCLUDED.procedure_description,
        procedure_status = EXCLUDED.procedure_status,
        procedure_method = EXCLUDED.procedure_method,
        procedure_method_details = EXCLUDED.procedure_method_details,
        procedure_category = EXCLUDED.procedure_category,
        procedure_value_amount = EXCLUDED.procedure_value_amount,
        procedure_value_currency = EXCLUDED.procedure_value_currency,
        suppliers_present = EXCLUDED.suppliers_present,
        awards_present = EXCLUDED.awards_present,
        contracts_present = EXCLUDED.contracts_present,
        updated_at = clock_timestamp()
    RETURNING id, created_at, updated_at
"""

_GET_PROCUREMENT = """
    SELECT *
    FROM procurements
    WHERE source = %(source)s AND external_id = %(external_id)s
    FOR SHARE
"""

_GET_SUPPLIERS = """
    SELECT ordinal, external_id, name
    FROM procurement_suppliers
    WHERE procurement_id = %(procurement_id)s
    ORDER BY ordinal
"""

_GET_AWARDS = """
    SELECT
        ordinal,
        external_id,
        status,
        award_date,
        value_amount,
        value_currency,
        suppliers_present
    FROM procurement_awards
    WHERE procurement_id = %(procurement_id)s
    ORDER BY ordinal
"""

_GET_AWARD_SUPPLIERS = """
    SELECT award_ordinal, ordinal, external_id, name
    FROM award_suppliers
    WHERE procurement_id = %(procurement_id)s
    ORDER BY award_ordinal, ordinal
"""

_GET_CONTRACTS = """
    SELECT
        ordinal,
        external_id,
        award_external_id,
        status,
        date_signed,
        value_amount,
        value_currency
    FROM procurement_contracts
    WHERE procurement_id = %(procurement_id)s
    ORDER BY ordinal
"""


class ProcurementRepository:
    """Persist and reconstruct source-independent procurement snapshots."""

    def __init__(self, database: PostgresDatabase) -> None:
        self._database = database

    async def save(self, record: ProcurementRecord) -> StoredProcurement:
        """Atomically upsert one current snapshot and replace all child facts."""
        async with self._database.connection() as connection:
            cursor = await connection.execute(
                _UPSERT_PROCUREMENT,
                self._parent_parameters(record),
            )
            parent = await cursor.fetchone()
            if parent is None:  # pragma: no cover - PostgreSQL RETURNING contract
                raise RuntimeError("PostgreSQL did not return the saved procurement")
            procurement_id: UUID = parent["id"]

            await self._delete_children(connection, procurement_id)
            await self._insert_suppliers(connection, procurement_id, record.suppliers)
            await self._insert_awards(connection, procurement_id, record.awards)
            await self._insert_contracts(connection, procurement_id, record.contracts)

            return StoredProcurement(
                id=procurement_id,
                record=record,
                created_at=self._utc(parent["created_at"]),
                updated_at=self._utc(parent["updated_at"]),
            )

    async def get(
        self,
        *,
        source: str,
        external_id: str,
    ) -> StoredProcurement | None:
        """Reconstruct one coherent snapshot inside a shared-lock transaction."""
        async with self._database.connection() as connection:
            cursor = await connection.execute(
                _GET_PROCUREMENT,
                {"source": source, "external_id": external_id},
            )
            parent = await cursor.fetchone()
            if parent is None:
                return None

            procurement_id: UUID = parent["id"]
            suppliers = await self._fetch_all(
                connection,
                _GET_SUPPLIERS,
                procurement_id,
            )
            awards = await self._fetch_all(
                connection,
                _GET_AWARDS,
                procurement_id,
            )
            award_suppliers = await self._fetch_all(
                connection,
                _GET_AWARD_SUPPLIERS,
                procurement_id,
            )
            contracts = await self._fetch_all(
                connection,
                _GET_CONTRACTS,
                procurement_id,
            )
            record = self._record_from_rows(
                parent,
                suppliers=suppliers,
                awards=awards,
                award_suppliers=award_suppliers,
                contracts=contracts,
            )
            return StoredProcurement(
                id=procurement_id,
                record=record,
                created_at=self._utc(parent["created_at"]),
                updated_at=self._utc(parent["updated_at"]),
            )

    @staticmethod
    def _parent_parameters(record: ProcurementRecord) -> Mapping[str, object]:
        reference = record.source_reference
        buyer = record.buyer
        procedure = record.procedure
        procedure_amount, procedure_currency = ProcurementRepository._money_columns(
            procedure.value if procedure is not None else None
        )
        return {
            "id": uuid4(),
            "source": reference.source,
            "external_id": reference.external_id,
            "evidence_id": reference.evidence_id,
            "buyer_present": buyer is not None,
            "buyer_external_id": buyer.external_id if buyer is not None else None,
            "buyer_name": buyer.name if buyer is not None else None,
            "procedure_external_id": (
                procedure.external_id if procedure is not None else None
            ),
            "procedure_title": procedure.title if procedure is not None else None,
            "procedure_description": (
                procedure.description if procedure is not None else None
            ),
            "procedure_status": procedure.status if procedure is not None else None,
            "procedure_method": procedure.method if procedure is not None else None,
            "procedure_method_details": (
                procedure.method_details if procedure is not None else None
            ),
            "procedure_category": (
                procedure.category if procedure is not None else None
            ),
            "procedure_value_amount": procedure_amount,
            "procedure_value_currency": procedure_currency,
            "suppliers_present": record.suppliers is not None,
            "awards_present": record.awards is not None,
            "contracts_present": record.contracts is not None,
        }

    @staticmethod
    async def _delete_children(
        connection: AsyncConnection[DictRow],
        procurement_id: UUID,
    ) -> None:
        parameters = {"procurement_id": procurement_id}
        await connection.execute(
            "DELETE FROM procurement_suppliers "
            "WHERE procurement_id = %(procurement_id)s",
            parameters,
        )
        await connection.execute(
            "DELETE FROM procurement_contracts "
            "WHERE procurement_id = %(procurement_id)s",
            parameters,
        )
        await connection.execute(
            "DELETE FROM procurement_awards WHERE procurement_id = %(procurement_id)s",
            parameters,
        )

    @staticmethod
    async def _insert_suppliers(
        connection: AsyncConnection[DictRow],
        procurement_id: UUID,
        suppliers: tuple[OrganizationRef, ...] | None,
    ) -> None:
        if suppliers is None:
            return
        for ordinal, supplier in enumerate(suppliers):
            await connection.execute(
                """
                INSERT INTO procurement_suppliers (
                    procurement_id, ordinal, external_id, name
                ) VALUES (
                    %(procurement_id)s, %(ordinal)s, %(external_id)s, %(name)s
                )
                """,
                {
                    "procurement_id": procurement_id,
                    "ordinal": ordinal,
                    "external_id": supplier.external_id,
                    "name": supplier.name,
                },
            )

    @classmethod
    async def _insert_awards(
        cls,
        connection: AsyncConnection[DictRow],
        procurement_id: UUID,
        awards: tuple[Award, ...] | None,
    ) -> None:
        if awards is None:
            return
        for award_ordinal, award in enumerate(awards):
            amount, currency = cls._money_columns(award.value)
            await connection.execute(
                """
                INSERT INTO procurement_awards (
                    procurement_id,
                    ordinal,
                    external_id,
                    status,
                    award_date,
                    value_amount,
                    value_currency,
                    suppliers_present
                ) VALUES (
                    %(procurement_id)s,
                    %(ordinal)s,
                    %(external_id)s,
                    %(status)s,
                    %(award_date)s,
                    %(value_amount)s,
                    %(value_currency)s,
                    %(suppliers_present)s
                )
                """,
                {
                    "procurement_id": procurement_id,
                    "ordinal": award_ordinal,
                    "external_id": award.external_id,
                    "status": award.status,
                    "award_date": award.date,
                    "value_amount": amount,
                    "value_currency": currency,
                    "suppliers_present": award.suppliers is not None,
                },
            )
            if award.suppliers is None:
                continue
            for supplier_ordinal, supplier in enumerate(award.suppliers):
                await connection.execute(
                    """
                    INSERT INTO award_suppliers (
                        procurement_id,
                        award_ordinal,
                        ordinal,
                        external_id,
                        name
                    ) VALUES (
                        %(procurement_id)s,
                        %(award_ordinal)s,
                        %(ordinal)s,
                        %(external_id)s,
                        %(name)s
                    )
                    """,
                    {
                        "procurement_id": procurement_id,
                        "award_ordinal": award_ordinal,
                        "ordinal": supplier_ordinal,
                        "external_id": supplier.external_id,
                        "name": supplier.name,
                    },
                )

    @classmethod
    async def _insert_contracts(
        cls,
        connection: AsyncConnection[DictRow],
        procurement_id: UUID,
        contracts: tuple[Contract, ...] | None,
    ) -> None:
        if contracts is None:
            return
        for ordinal, contract in enumerate(contracts):
            amount, currency = cls._money_columns(contract.value)
            await connection.execute(
                """
                INSERT INTO procurement_contracts (
                    procurement_id,
                    ordinal,
                    external_id,
                    award_external_id,
                    status,
                    date_signed,
                    value_amount,
                    value_currency
                ) VALUES (
                    %(procurement_id)s,
                    %(ordinal)s,
                    %(external_id)s,
                    %(award_external_id)s,
                    %(status)s,
                    %(date_signed)s,
                    %(value_amount)s,
                    %(value_currency)s
                )
                """,
                {
                    "procurement_id": procurement_id,
                    "ordinal": ordinal,
                    "external_id": contract.external_id,
                    "award_external_id": contract.award_external_id,
                    "status": contract.status,
                    "date_signed": contract.date_signed,
                    "value_amount": amount,
                    "value_currency": currency,
                },
            )

    @staticmethod
    async def _fetch_all(
        connection: AsyncConnection[DictRow],
        query: str,
        procurement_id: UUID,
    ) -> list[DictRow]:
        cursor = await connection.execute(
            query,
            {"procurement_id": procurement_id},
        )
        return await cursor.fetchall()

    @classmethod
    def _record_from_rows(
        cls,
        parent: Mapping[str, Any],
        *,
        suppliers: list[DictRow],
        awards: list[DictRow],
        award_suppliers: list[DictRow],
        contracts: list[DictRow],
    ) -> ProcurementRecord:
        supplier_rows_by_award: dict[int, list[DictRow]] = {}
        for row in award_suppliers:
            supplier_rows_by_award.setdefault(row["award_ordinal"], []).append(row)

        mapped_awards = tuple(
            Award(
                external_id=row["external_id"],
                status=row["status"],
                date=cls._optional_utc(row["award_date"]),
                value=cls._money_from_columns(
                    row["value_amount"],
                    row["value_currency"],
                ),
                suppliers=(
                    tuple(
                        cls._organization_from_row(supplier)
                        for supplier in supplier_rows_by_award.get(row["ordinal"], [])
                    )
                    if row["suppliers_present"]
                    else None
                ),
            )
            for row in awards
        )
        mapped_contracts = tuple(
            Contract(
                external_id=row["external_id"],
                award_external_id=row["award_external_id"],
                status=row["status"],
                date_signed=cls._optional_utc(row["date_signed"]),
                value=cls._money_from_columns(
                    row["value_amount"],
                    row["value_currency"],
                ),
            )
            for row in contracts
        )
        procedure = cls._procedure_from_parent(parent)
        return ProcurementRecord(
            source_reference=SourceReference(
                source=parent["source"],
                external_id=parent["external_id"],
                evidence_id=parent["evidence_id"],
            ),
            buyer=(
                OrganizationRef(
                    external_id=parent["buyer_external_id"],
                    name=parent["buyer_name"],
                )
                if parent["buyer_present"]
                else None
            ),
            suppliers=(
                tuple(cls._organization_from_row(row) for row in suppliers)
                if parent["suppliers_present"]
                else None
            ),
            procedure=procedure,
            awards=mapped_awards if parent["awards_present"] else None,
            contracts=mapped_contracts if parent["contracts_present"] else None,
        )

    @classmethod
    def _procedure_from_parent(
        cls,
        parent: Mapping[str, Any],
    ) -> ProcurementProcedure | None:
        if parent["procedure_external_id"] is None:
            return None
        return ProcurementProcedure(
            external_id=parent["procedure_external_id"],
            title=parent["procedure_title"],
            description=parent["procedure_description"],
            status=parent["procedure_status"],
            method=parent["procedure_method"],
            method_details=parent["procedure_method_details"],
            category=parent["procedure_category"],
            value=cls._money_from_columns(
                parent["procedure_value_amount"],
                parent["procedure_value_currency"],
            ),
        )

    @staticmethod
    def _organization_from_row(row: Mapping[str, Any]) -> OrganizationRef:
        return OrganizationRef(external_id=row["external_id"], name=row["name"])

    @staticmethod
    def _money_columns(money: Money | None) -> tuple[Decimal | None, str | None]:
        if money is None:
            return None, None
        return money.amount, money.currency

    @staticmethod
    def _money_from_columns(
        amount: Decimal | None,
        currency: str | None,
    ) -> Money | None:
        if amount is None:
            return None
        return Money(amount=amount, currency=currency)

    @staticmethod
    def _utc(value: datetime) -> datetime:
        return value.astimezone(UTC)

    @classmethod
    def _optional_utc(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return cls._utc(value)
