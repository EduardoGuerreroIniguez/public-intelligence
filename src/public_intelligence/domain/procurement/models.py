"""Source-independent factual procurement value objects."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True, slots=True)
class SourceReference:
    """Namespaced external identity and optional raw-evidence reference."""

    source: str
    external_id: str
    evidence_id: UUID | None = None

    def __post_init__(self) -> None:
        if not self.source.strip():
            raise ValueError("source must not be blank")
        if not self.external_id.strip():
            raise ValueError("external_id must not be blank")


@dataclass(frozen=True, slots=True)
class OrganizationRef:
    """Unresolved reference to a source-observed organization."""

    external_id: str | None
    name: str | None


@dataclass(frozen=True, slots=True)
class Money:
    """Exact decimal amount with only source-supplied currency information."""

    amount: Decimal
    currency: str | None

    def __post_init__(self) -> None:
        if not isinstance(self.amount, Decimal):
            raise TypeError("amount must be a Decimal")
        if not self.amount.is_finite():
            raise ValueError("amount must be finite")


@dataclass(frozen=True, slots=True)
class ProcurementProcedure:
    """Minimal observed tender/procedure facts."""

    external_id: str
    title: str | None
    description: str | None
    status: str | None
    method: str | None
    method_details: str | None
    category: str | None
    value: Money | None


@dataclass(frozen=True, slots=True)
class Award:
    """Minimal observed procurement award facts."""

    external_id: str
    status: str | None
    date: datetime | None
    value: Money | None
    suppliers: tuple[OrganizationRef, ...] | None

    def __post_init__(self) -> None:
        _require_utc(self.date, field="date")


@dataclass(frozen=True, slots=True)
class Contract:
    """Minimal observed procurement contract facts."""

    external_id: str
    award_external_id: str | None
    status: str | None
    date_signed: datetime | None
    value: Money | None

    def __post_init__(self) -> None:
        _require_utc(self.date_signed, field="date_signed")


@dataclass(frozen=True, slots=True)
class ProcurementRecord:
    """Source-independent factual snapshot of one procurement process."""

    source_reference: SourceReference
    buyer: OrganizationRef | None
    suppliers: tuple[OrganizationRef, ...] | None
    procedure: ProcurementProcedure | None
    awards: tuple[Award, ...] | None
    contracts: tuple[Contract, ...] | None


def _require_utc(value: datetime | None, *, field: str) -> None:
    if value is None:
        return
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field} must be timezone-aware")
    if value.utcoffset() != timedelta(0):
        raise ValueError(f"{field} must be normalized to UTC")
