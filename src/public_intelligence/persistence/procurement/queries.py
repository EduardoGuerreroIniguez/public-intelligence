"""Source-independent queries over normalized procurement snapshots."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from public_intelligence.domain.procurement import Money

from ..database import PostgresDatabase
from .models import StoredProcurement
from .repository import ProcurementRepository

_MAX_LIMIT = 200


@dataclass(frozen=True, slots=True)
class ProcurementSearch:
    """Validated filters for one bounded normalized-procurement search."""

    buyer: str | None = None
    supplier: str | None = None
    status: str | None = None
    currency: str | None = None
    min_value: Decimal | None = None
    max_value: Decimal | None = None
    limit: int = 50
    offset: int = 0

    def __post_init__(self) -> None:
        for name in ("buyer", "supplier", "status", "currency"):
            value = getattr(self, name)
            if value is None:
                continue
            if not isinstance(value, str):
                raise TypeError(f"{name} must be a string when provided")
            if not value.strip():
                raise ValueError(f"{name} must not be blank")

        for name in ("min_value", "max_value"):
            value = getattr(self, name)
            if value is None:
                continue
            if not isinstance(value, Decimal):
                raise TypeError(f"{name} must be a Decimal when provided")
            if not value.is_finite():
                raise ValueError(f"{name} must be finite")

        if (
            self.min_value is not None
            and self.max_value is not None
            and self.min_value > self.max_value
        ):
            raise ValueError("min_value must be less than or equal to max_value")
        if (
            self.min_value is not None or self.max_value is not None
        ) and self.currency is None:
            raise ValueError("currency is required for value range filters")

        if isinstance(self.limit, bool) or not isinstance(self.limit, int):
            raise TypeError("limit must be an integer")
        if not 1 <= self.limit <= _MAX_LIMIT:
            raise ValueError(f"limit must be between 1 and {_MAX_LIMIT}")
        if isinstance(self.offset, bool) or not isinstance(self.offset, int):
            raise TypeError("offset must be an integer")
        if self.offset < 0:
            raise ValueError("offset must be greater than or equal to 0")


@dataclass(frozen=True, slots=True)
class ProcurementSearchResult:
    """Minimal factual projection for one normalized procurement."""

    source: str
    external_id: str
    buyer_name: str | None
    procedure_title: str | None
    procedure_status: str | None
    procedure_value: Money | None
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class ProcurementSearchPage:
    """One bounded result page and the total matching row count."""

    items: tuple[ProcurementSearchResult, ...]
    total: int
    limit: int
    offset: int


class ProcurementQueries:
    """Read normalized procurement facts without exposing relational layout."""

    def __init__(self, database: PostgresDatabase) -> None:
        self._database = database
        self._detail_repository = ProcurementRepository(database)

    async def search(self, criteria: ProcurementSearch) -> ProcurementSearchPage:
        """Return one deterministically ordered page of normalized facts."""
        where, parameters = _search_conditions(criteria)
        query = f"""
            WITH filtered AS (
                SELECT
                    p.source,
                    p.external_id,
                    p.buyer_name,
                    p.procedure_title,
                    p.procedure_status,
                    p.procedure_value_amount,
                    p.procedure_value_currency,
                    p.updated_at
                FROM procurements AS p
                WHERE {where}
            ),
            paged AS (
                SELECT *
                FROM filtered
                ORDER BY updated_at DESC, source ASC, external_id ASC
                LIMIT %(limit)s OFFSET %(offset)s
            ),
            totals AS (
                SELECT count(*)::bigint AS total
                FROM filtered
            )
            SELECT paged.*, totals.total
            FROM totals
            LEFT JOIN paged ON TRUE
            ORDER BY
                paged.updated_at DESC,
                paged.source ASC,
                paged.external_id ASC
        """
        async with self._database.connection() as connection:
            cursor = await connection.execute(query, parameters)
            rows = await cursor.fetchall()

        total = int(rows[0]["total"])
        items = tuple(
            _result_from_row(row) for row in rows if row["source"] is not None
        )
        return ProcurementSearchPage(
            items=items,
            total=total,
            limit=criteria.limit,
            offset=criteria.offset,
        )

    async def get(
        self,
        *,
        source: str,
        external_id: str,
    ) -> StoredProcurement | None:
        """Delegate full-detail reconstruction to ``ProcurementRepository``."""
        return await self._detail_repository.get(
            source=source,
            external_id=external_id,
        )


def _search_conditions(
    criteria: ProcurementSearch,
) -> tuple[str, dict[str, object]]:
    conditions: list[str] = []
    parameters: dict[str, object] = {
        "limit": criteria.limit,
        "offset": criteria.offset,
    }

    if criteria.buyer is not None:
        conditions.append("p.buyer_name ILIKE %(buyer)s ESCAPE E'\\\\'")
        parameters["buyer"] = _literal_substring_pattern(criteria.buyer)
    if criteria.supplier is not None:
        conditions.append(
            """
            EXISTS (
                SELECT 1
                FROM procurement_suppliers AS supplier
                WHERE supplier.procurement_id = p.id
                  AND supplier.name ILIKE %(supplier)s ESCAPE E'\\\\'
            )
            """
        )
        parameters["supplier"] = _literal_substring_pattern(criteria.supplier)
    if criteria.status is not None:
        conditions.append("p.procedure_status = %(status)s")
        parameters["status"] = criteria.status
    if criteria.currency is not None:
        conditions.append("p.procedure_value_currency = %(currency)s")
        parameters["currency"] = criteria.currency
    if criteria.min_value is not None:
        conditions.append("p.procedure_value_amount >= %(min_value)s")
        parameters["min_value"] = criteria.min_value
    if criteria.max_value is not None:
        conditions.append("p.procedure_value_amount <= %(max_value)s")
        parameters["max_value"] = criteria.max_value

    return " AND ".join(conditions) if conditions else "TRUE", parameters


def _literal_substring_pattern(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _result_from_row(row: Mapping[str, Any]) -> ProcurementSearchResult:
    amount: Decimal | None = row["procedure_value_amount"]
    money = (
        None
        if amount is None
        else Money(amount=amount, currency=row["procedure_value_currency"])
    )
    return ProcurementSearchResult(
        source=row["source"],
        external_id=row["external_id"],
        buyer_name=row["buyer_name"],
        procedure_title=row["procedure_title"],
        procedure_status=row["procedure_status"],
        procedure_value=money,
        updated_at=row["updated_at"].astimezone(UTC),
    )
