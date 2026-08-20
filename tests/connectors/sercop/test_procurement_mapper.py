import json
from copy import deepcopy
from datetime import UTC, datetime
from decimal import Decimal
from hashlib import sha256
from uuid import uuid4

import pytest

from public_intelligence.connectors.sercop import (
    SercopAmbiguousProcurementIdentityError,
    SercopInvalidDateError,
    SercopInvalidMoneyError,
    SercopMissingProcurementIdentityError,
    SercopRecordPackage,
    SercopUnsupportedReleaseStructureError,
    map_procurement_package,
)
from public_intelligence.connectors.sercop.models import SercopMonetaryValue
from public_intelligence.domain.procurement import OrganizationRef
from public_intelligence.persistence import RawEvidenceInput, RawEvidenceRepository

CATALOG_FIXTURE = "record-2015-ocds-5wno2w-CE-20150000092768-23237.json"
ARTISTIC_FIXTURE = "record-2026-ocds-5wno2w-RE-OACL-GADMSFD-2026-001-2452.json"


def test_maps_exact_supported_procurement_fields(
    record_bodies: dict[str, bytes],
) -> None:
    evidence_id = uuid4()
    package = _package(record_bodies, CATALOG_FIXTURE)
    record = map_procurement_package(
        package,
        evidence_id=evidence_id,
    )
    source_release = package.releases[0]
    assert source_release.tender is not None

    assert record.source_reference.source == "sercop"
    assert record.source_reference.external_id == "ocds-5wno2w-CE-20150000092768-23237"
    assert record.source_reference.evidence_id == evidence_id
    assert record.buyer == OrganizationRef(
        external_id="EC-RUC-0160007280001",
        name=(
            "DIRECCION DISTRITAL 01D01 PARROQUIAS URBANAS: MACHANGARA A "
            "BELLAVISTA Y PARROQUIAS RURALES: NULTI A SAYAUSI - SALUD"
        ),
    )
    assert record.procedure is not None
    assert record.procedure.external_id == "CE-20150000092768-23237"
    assert record.procedure.title == "Orden de compra CE-20150000092768"
    assert record.procedure.description == source_release.tender.description
    assert record.procedure.status == "complete"
    assert record.procedure.method == "direct"
    assert (
        record.procedure.method_details
        == source_release.tender.procurement_method_details
    )
    assert record.procedure.category is None
    assert record.procedure.value is not None
    assert record.procedure.value.amount == Decimal("24.2")
    assert record.procedure.value.currency == "USD"

    assert record.awards is not None
    assert source_release.awards is not None
    assert len(record.awards) == 1
    award = record.awards[0]
    assert award.external_id == source_release.awards[0].id
    assert award.status == source_release.awards[0].status
    assert award.date is None
    assert award.value == record.procedure.value
    assert award.suppliers == record.suppliers

    assert record.contracts is not None
    assert source_release.contracts is not None
    assert len(record.contracts) == 1
    contract = record.contracts[0]
    assert contract.external_id == source_release.contracts[0].id
    assert contract.award_external_id == source_release.contracts[0].award_id
    assert contract.award_external_id == award.external_id
    assert contract.status == source_release.contracts[0].status
    assert contract.date_signed is None
    assert contract.value is None


def test_valid_source_datetime_is_normalized_to_utc(
    record_bodies: dict[str, bytes],
) -> None:
    record = map_procurement_package(_package(record_bodies, ARTISTIC_FIXTURE))

    assert record.awards is not None
    assert record.awards[0].status is None
    assert record.awards[0].date == datetime(2026, 7, 24, 0, 3, 39, tzinfo=UTC)
    assert record.procedure is not None
    assert record.procedure.category == "services"
    assert record.contracts is None


def test_contract_datetime_is_normalized_to_utc(
    record_bodies: dict[str, bytes],
) -> None:
    package = _package(record_bodies, CATALOG_FIXTURE)
    release = package.releases[0]
    assert release.contracts is not None
    value = SercopMonetaryValue.model_validate({"amount": 15.25, "currency": "USD"})
    contract = release.contracts[0].model_copy(
        update={
            "date_signed": "2015-01-15T08:30:00-05:00",
            "value": value,
        }
    )
    updated = release.model_copy(update={"contracts": [contract]})

    record = map_procurement_package(package.model_copy(update={"releases": [updated]}))

    assert record.contracts is not None
    assert record.contracts[0].date_signed == datetime(2015, 1, 15, 13, 30, tzinfo=UTC)
    assert record.contracts[0].value is not None
    assert record.contracts[0].value.amount == Decimal("15.25")
    assert record.contracts[0].value.currency == "USD"


@pytest.mark.parametrize("ocid", ["", "  "])
def test_blank_procurement_identity_is_rejected(
    record_bodies: dict[str, bytes],
    ocid: str,
) -> None:
    package = _package(record_bodies, CATALOG_FIXTURE)
    release = package.releases[0].model_copy(update={"ocid": ocid})

    with pytest.raises(SercopMissingProcurementIdentityError):
        map_procurement_package(package.model_copy(update={"releases": [release]}))


def test_distinct_ocids_are_ambiguous(record_bodies: dict[str, bytes]) -> None:
    package = _package(record_bodies, CATALOG_FIXTURE)
    release = package.releases[0]
    other = release.model_copy(update={"id": "second", "ocid": "ocds-second"})

    with pytest.raises(SercopAmbiguousProcurementIdentityError) as captured:
        map_procurement_package(
            package.model_copy(update={"releases": [release, other]})
        )

    assert captured.value.ocids == (release.ocid, "ocds-second")


def test_same_ocid_multiple_releases_are_unsupported(
    record_bodies: dict[str, bytes],
) -> None:
    package = _package(record_bodies, CATALOG_FIXTURE)
    release = package.releases[0]
    other = release.model_copy(update={"id": "second"})

    with pytest.raises(SercopUnsupportedReleaseStructureError, match="multiple"):
        map_procurement_package(
            package.model_copy(update={"releases": [release, other]})
        )


def test_zero_releases_are_unsupported(record_bodies: dict[str, bytes]) -> None:
    package = _package(record_bodies, CATALOG_FIXTURE)

    with pytest.raises(SercopUnsupportedReleaseStructureError, match="no releases"):
        map_procurement_package(package.model_copy(update={"releases": []}))


def test_missing_buyer_remains_none(record_bodies: dict[str, bytes]) -> None:
    package = _package(record_bodies, CATALOG_FIXTURE)
    release = package.releases[0].model_copy(update={"buyer": None})

    record = map_procurement_package(package.model_copy(update={"releases": [release]}))

    assert record.buyer is None


@pytest.mark.parametrize(
    ("source_suppliers", "expected"),
    [
        (None, None),
        ([], ()),
    ],
)
def test_supplier_absence_and_explicit_empty_collection_are_preserved(
    record_bodies: dict[str, bytes],
    source_suppliers: list[object] | None,
    expected: tuple[()] | None,
) -> None:
    package = _package(record_bodies, CATALOG_FIXTURE)
    release = package.releases[0]
    assert release.awards is not None
    award = release.awards[0].model_copy(update={"suppliers": source_suppliers})
    updated = release.model_copy(update={"awards": [award]})

    record = map_procurement_package(package.model_copy(update={"releases": [updated]}))

    assert record.awards is not None
    assert record.awards[0].suppliers == expected
    assert record.suppliers == expected


def test_suppliers_are_deduplicated_only_by_exact_equality(
    record_bodies: dict[str, bytes],
) -> None:
    package = _package(record_bodies, CATALOG_FIXTURE)
    release = package.releases[0]
    assert release.awards is not None
    award = release.awards[0]
    assert award.suppliers is not None
    supplier = award.suppliers[0]
    renamed = supplier.model_copy(update={"name": f"{supplier.name} altered"})
    first_award = award.model_copy(update={"suppliers": [supplier]})
    second_award = award.model_copy(
        update={"id": "second-award", "suppliers": [supplier, renamed]}
    )
    updated = release.model_copy(update={"awards": [first_award, second_award]})

    record = map_procurement_package(package.model_copy(update={"releases": [updated]}))

    assert record.suppliers == (
        OrganizationRef(external_id=supplier.id, name=supplier.name),
        OrganizationRef(external_id=renamed.id, name=renamed.name),
    )


@pytest.mark.parametrize(
    "source",
    [
        {"amount": 100},
        {"amount": 100, "currency": None},
    ],
)
def test_source_money_accepts_absent_or_null_currency(
    source: dict[str, object],
) -> None:
    value = SercopMonetaryValue.model_validate(source)

    assert value.amount == 100
    assert value.currency is None


def test_zero_and_missing_currency_map_without_inference(
    record_bodies: dict[str, bytes],
) -> None:
    package = _package(record_bodies, CATALOG_FIXTURE)
    release = package.releases[0]
    assert release.tender is not None
    value = SercopMonetaryValue.model_validate({"amount": 0})
    tender = release.tender.model_copy(update={"value": value})
    updated = release.model_copy(update={"tender": tender})

    record = map_procurement_package(package.model_copy(update={"releases": [updated]}))

    assert record.procedure is not None
    assert record.procedure.value is not None
    assert record.procedure.value.amount == Decimal("0")
    assert record.procedure.value.currency is None


def test_missing_money_remains_none(record_bodies: dict[str, bytes]) -> None:
    package = _package(record_bodies, CATALOG_FIXTURE)
    release = package.releases[0]
    assert release.tender is not None
    tender = release.tender.model_copy(update={"value": None})
    updated = release.model_copy(update={"tender": tender})

    record = map_procurement_package(package.model_copy(update={"releases": [updated]}))

    assert record.procedure is not None
    assert record.procedure.value is None


def test_nonfinite_money_fails_explicitly(record_bodies: dict[str, bytes]) -> None:
    package = _package(record_bodies, CATALOG_FIXTURE)
    release = package.releases[0]
    assert release.tender is not None
    value = SercopMonetaryValue.model_validate({"amount": float("nan")})
    tender = release.tender.model_copy(update={"value": value})
    updated = release.model_copy(update={"tender": tender})

    with pytest.raises(SercopInvalidMoneyError) as captured:
        map_procurement_package(package.model_copy(update={"releases": [updated]}))

    assert captured.value.field == "tender.value"


@pytest.mark.parametrize("value", ["not-a-date", "2026-07-23T19:03:39"])
def test_unusable_or_naive_mapped_datetime_fails(
    record_bodies: dict[str, bytes],
    value: str,
) -> None:
    package = _package(record_bodies, ARTISTIC_FIXTURE)
    release = package.releases[0]
    assert release.awards is not None
    award = release.awards[0].model_copy(update={"date": value})
    updated = release.model_copy(update={"awards": [award]})

    with pytest.raises(SercopInvalidDateError) as captured:
        map_procurement_package(package.model_copy(update={"releases": [updated]}))

    assert captured.value.field == "awards[0].date"


def test_optional_source_sections_preserve_absent_and_empty(
    record_bodies: dict[str, bytes],
) -> None:
    package = _package(record_bodies, CATALOG_FIXTURE)
    release = package.releases[0].model_copy(
        update={"tender": None, "awards": None, "contracts": []}
    )

    record = map_procurement_package(package.model_copy(update={"releases": [release]}))

    assert record.procedure is None
    assert record.awards is None
    assert record.suppliers is None
    assert record.contracts == ()


def test_additive_source_fields_do_not_affect_mapping(
    record_bodies: dict[str, bytes],
) -> None:
    source = deepcopy(json.loads(record_bodies[CATALOG_FIXTURE]))
    source["futurePackageField"] = {"preserved": True}
    source["releases"][0]["futureReleaseField"] = True
    package = SercopRecordPackage.model_validate(source)

    record = map_procurement_package(package)

    assert record.source_reference.external_id == package.releases[0].ocid


@pytest.mark.anyio
async def test_persisted_package_evidence_can_be_validated_and_mapped(
    repository: RawEvidenceRepository,
    record_bodies: dict[str, bytes],
) -> None:
    source = json.loads(record_bodies[CATALOG_FIXTURE])
    payload = json.dumps(
        source,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    ocid = source["releases"][0]["ocid"]
    saved = await repository.save(
        RawEvidenceInput(
            source="sercop",
            mechanism="bulk_partition_release_package",
            source_key=ocid,
            endpoint="https://sercop.test/download",
            parameters={"serialization": "canonical-json-v1"},
            retrieved_at=datetime(2026, 8, 20, tzinfo=UTC),
            http_status=200,
            content_type="application/json",
            payload_sha256=sha256(payload).hexdigest(),
            payload_byte_size=len(payload),
            payload=payload,
        )
    )
    loaded = await repository.get(saved.id)
    assert loaded is not None

    package = SercopRecordPackage.model_validate_json(loaded.payload)
    record = map_procurement_package(package, evidence_id=loaded.id)

    assert record.source_reference.external_id == ocid
    assert record.source_reference.evidence_id == loaded.id


def _package(
    record_bodies: dict[str, bytes],
    fixture_name: str,
) -> SercopRecordPackage:
    return SercopRecordPackage.model_validate_json(record_bodies[fixture_name])
