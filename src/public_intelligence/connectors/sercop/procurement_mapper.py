"""Translate validated SERCOP source packages into procurement facts."""

from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from uuid import UUID

from public_intelligence.domain.procurement import (
    Award,
    Contract,
    Money,
    OrganizationRef,
    ProcurementProcedure,
    ProcurementRecord,
    SourceReference,
)

from .errors import (
    SercopAmbiguousProcurementIdentityError,
    SercopInvalidDateError,
    SercopInvalidMoneyError,
    SercopMissingProcurementIdentityError,
    SercopUnsupportedReleaseStructureError,
)
from .models import (
    SercopAward,
    SercopContract,
    SercopMonetaryValue,
    SercopOrganizationReference,
    SercopRecordPackage,
    SercopTender,
)


def map_procurement_package(
    package: SercopRecordPackage,
    *,
    evidence_id: UUID | None = None,
) -> ProcurementRecord:
    """Map the one-release package shape supported by current SERCOP evidence."""
    releases = package.releases
    if not releases:
        raise SercopUnsupportedReleaseStructureError(
            reason="release package contains no releases"
        )

    ocids = [release.ocid for release in releases]
    if any(not ocid.strip() for ocid in ocids):
        raise SercopMissingProcurementIdentityError()

    distinct_ocids = tuple(dict.fromkeys(ocids))
    if len(distinct_ocids) > 1:
        raise SercopAmbiguousProcurementIdentityError(ocids=distinct_ocids)
    if len(releases) > 1:
        raise SercopUnsupportedReleaseStructureError(
            reason="multiple releases require an unverified selection or merge rule"
        )

    release = releases[0]
    awards = (
        None
        if release.awards is None
        else tuple(
            _map_award(award, index=index) for index, award in enumerate(release.awards)
        )
    )
    contracts = (
        None
        if release.contracts is None
        else tuple(
            _map_contract(contract, index=index)
            for index, contract in enumerate(release.contracts)
        )
    )
    return ProcurementRecord(
        source_reference=SourceReference(
            source="sercop",
            external_id=release.ocid,
            evidence_id=evidence_id,
        ),
        buyer=_map_organization(release.buyer),
        suppliers=_aggregate_suppliers(awards),
        procedure=_map_procedure(release.tender),
        awards=awards,
        contracts=contracts,
    )


def _map_organization(
    organization: SercopOrganizationReference | None,
) -> OrganizationRef | None:
    if organization is None:
        return None
    return OrganizationRef(external_id=organization.id, name=organization.name)


def _map_procedure(tender: SercopTender | None) -> ProcurementProcedure | None:
    if tender is None:
        return None
    return ProcurementProcedure(
        external_id=tender.id,
        title=tender.title,
        description=tender.description,
        status=tender.status,
        method=tender.procurement_method,
        method_details=tender.procurement_method_details,
        category=tender.main_procurement_category,
        value=_map_money(tender.value, field="tender.value"),
    )


def _map_award(award: SercopAward, *, index: int) -> Award:
    suppliers = (
        None
        if award.suppliers is None
        else tuple(
            OrganizationRef(external_id=supplier.id, name=supplier.name)
            for supplier in award.suppliers
        )
    )
    return Award(
        external_id=award.id,
        status=award.status,
        date=_map_datetime(award.date, field=f"awards[{index}].date"),
        value=_map_money(award.value, field=f"awards[{index}].value"),
        suppliers=suppliers,
    )


def _map_contract(contract: SercopContract, *, index: int) -> Contract:
    return Contract(
        external_id=contract.id,
        award_external_id=contract.award_id,
        status=contract.status,
        date_signed=_map_datetime(
            contract.date_signed,
            field=f"contracts[{index}].dateSigned",
        ),
        value=_map_money(contract.value, field=f"contracts[{index}].value"),
    )


def _aggregate_suppliers(
    awards: tuple[Award, ...] | None,
) -> tuple[OrganizationRef, ...] | None:
    if awards is None:
        return None

    supplied_collection = False
    unique: dict[OrganizationRef, None] = {}
    for award in awards:
        if award.suppliers is None:
            continue
        supplied_collection = True
        for supplier in award.suppliers:
            unique.setdefault(supplier, None)
    if not supplied_collection:
        return None
    return tuple(unique)


def _map_money(value: SercopMonetaryValue | None, *, field: str) -> Money | None:
    if value is None:
        return None
    try:
        amount = Decimal(str(value.amount))
        return Money(amount=amount, currency=value.currency)
    except (InvalidOperation, TypeError, ValueError) as error:
        raise SercopInvalidMoneyError(field=field) from error


def _map_datetime(value: str | None, *, field: str) -> datetime | None:
    if value is None:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise SercopInvalidDateError(field=field) from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise SercopInvalidDateError(field=field)
    return parsed.astimezone(UTC)
