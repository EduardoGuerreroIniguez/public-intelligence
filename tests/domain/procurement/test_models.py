from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from public_intelligence.domain.procurement import (
    Award,
    Contract,
    Money,
    OrganizationRef,
    ProcurementProcedure,
    ProcurementRecord,
    SourceReference,
)


def test_procurement_domain_can_be_constructed_without_source_models() -> None:
    evidence_id = uuid4()
    supplier = OrganizationRef(external_id="supplier-1", name="Supplier")
    value = Money(amount=Decimal("0"), currency=None)
    record = ProcurementRecord(
        source_reference=SourceReference(
            source="example_source",
            external_id="process-1",
            evidence_id=evidence_id,
        ),
        buyer=None,
        suppliers=(supplier,),
        procedure=ProcurementProcedure(
            external_id="procedure-1",
            title=None,
            description=None,
            status="open",
            method="direct",
            method_details=None,
            category=None,
            value=value,
        ),
        awards=(
            Award(
                external_id="award-1",
                status=None,
                date=datetime(2026, 8, 20, tzinfo=UTC),
                value=value,
                suppliers=(supplier,),
            ),
        ),
        contracts=(
            Contract(
                external_id="contract-1",
                award_external_id="award-1",
                status="active",
                date_signed=None,
                value=None,
            ),
        ),
    )

    assert record.source_reference.evidence_id == evidence_id
    assert record.procedure is not None
    assert record.procedure.value == Money(amount=Decimal("0"), currency=None)


def test_domain_models_are_immutable() -> None:
    reference = SourceReference(source="source", external_id="external")

    with pytest.raises(FrozenInstanceError):
        reference.external_id = "changed"  # type: ignore[misc]


@pytest.mark.parametrize("value", [Decimal("NaN"), Decimal("Infinity")])
def test_money_requires_finite_decimal(value: Decimal) -> None:
    with pytest.raises(ValueError, match="finite"):
        Money(amount=value, currency=None)


def test_money_requires_decimal() -> None:
    with pytest.raises(TypeError, match="Decimal"):
        Money(amount=1.5, currency=None)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "value",
    [
        datetime(2026, 8, 20),
        datetime(2026, 8, 20, tzinfo=timezone(timedelta(hours=-5))),
    ],
)
def test_domain_dates_must_be_timezone_aware_utc(value: datetime) -> None:
    with pytest.raises(ValueError):
        Award(
            external_id="award",
            status=None,
            date=value,
            value=None,
            suppliers=None,
        )


@pytest.mark.parametrize("source", ["", "  "])
def test_source_reference_requires_nonblank_namespace(source: str) -> None:
    with pytest.raises(ValueError, match="source"):
        SourceReference(source=source, external_id="external")


@pytest.mark.parametrize("external_id", ["", "  "])
def test_source_reference_requires_nonblank_external_id(external_id: str) -> None:
    with pytest.raises(ValueError, match="external_id"):
        SourceReference(source="source", external_id=external_id)
