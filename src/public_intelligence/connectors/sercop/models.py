"""Typed DTOs for source structures observed in SERCOP fixtures."""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StrictFloat, StrictInt, StrictStr


class _SercopModel(BaseModel):
    """Shared source-local behavior without imposing global strict mode."""

    model_config = ConfigDict(extra="allow", frozen=True, populate_by_name=True)


class SercopSearchSummary(_SercopModel):
    """Source-specific summary returned by ``search_ocds``."""

    id: StrictInt
    ocid: StrictStr
    year: StrictInt
    month: StrictInt
    method: StrictStr | None
    internal_type: StrictStr | None
    locality: StrictStr
    region: StrictStr
    suppliers: StrictStr | None
    buyer: StrictStr
    amount: StrictStr | None
    date: StrictStr
    title: StrictStr | None
    description: StrictStr | None
    budget: StrictStr | None


class SercopSearchPage(_SercopModel):
    """One explicit page of SERCOP search summaries."""

    total: StrictInt
    page: StrictInt
    pages: StrictInt
    data: list[SercopSearchSummary]

    @property
    def has_next(self) -> bool:
        """Whether source pagination reports a subsequent page."""
        return self.page < self.pages


class SercopPublisher(_SercopModel):
    """Publisher metadata attached to a SERCOP package."""

    uid: StrictStr
    name: StrictStr
    uri: StrictStr | None = None
    scheme: StrictStr | None = None


class SercopOrganizationReference(_SercopModel):
    """A source-provided reference to a buyer or supplier."""

    id: StrictStr
    name: StrictStr


class SercopIdentifier(_SercopModel):
    """A source-provided organization identifier."""

    id: StrictStr
    scheme: StrictStr
    legal_name: StrictStr = Field(alias="legalName")


class SercopParty(_SercopModel):
    """The typed identity core of an observed SERCOP party."""

    id: StrictStr
    name: StrictStr
    roles: list[StrictStr]
    identifier: SercopIdentifier | None = None


SercopNumber = StrictInt | StrictFloat


class SercopMonetaryValue(_SercopModel):
    """A source-level amount and its explicitly supplied currency."""

    amount: SercopNumber
    currency: StrictStr


class SercopTender(_SercopModel):
    """The non-exhaustive tender core exercised by captured fixtures."""

    id: StrictStr
    title: StrictStr | None = None
    description: StrictStr | None = None
    status: StrictStr | None = None
    procurement_method: StrictStr | None = Field(
        default=None, alias="procurementMethod"
    )
    procurement_method_details: StrictStr | None = Field(
        default=None, alias="procurementMethodDetails"
    )
    main_procurement_category: StrictStr | None = Field(
        default=None, alias="mainProcurementCategory"
    )
    value: SercopMonetaryValue | None = None
    procuring_entity: SercopOrganizationReference | None = Field(
        default=None, alias="procuringEntity"
    )


class SercopAward(_SercopModel):
    """The non-exhaustive award core exercised by captured fixtures."""

    id: StrictStr
    title: StrictStr | None = None
    description: StrictStr | None = None
    status: StrictStr | None = None
    date: StrictStr | None = None
    value: SercopMonetaryValue | None = None
    suppliers: list[SercopOrganizationReference] | None = None


class SercopContract(_SercopModel):
    """The non-exhaustive contract core exercised by captured fixtures."""

    id: StrictStr
    award_id: StrictStr | None = Field(default=None, alias="awardID")
    status: StrictStr | None = None
    date_signed: StrictStr | None = Field(default=None, alias="dateSigned")
    value: SercopMonetaryValue | None = None


class SercopRelatedProcess(_SercopModel):
    """A relationship to another source contracting process."""

    id: StrictStr
    title: StrictStr | None = None
    scheme: StrictStr | None = None
    identifier: StrictStr | None = None
    relationship: list[StrictStr] | None = None


class SercopRelease(_SercopModel):
    """A source release inside the observed SERCOP package shape."""

    id: StrictStr
    date: StrictStr
    tag: list[StrictStr]
    ocid: StrictStr
    initiation_type: StrictStr | None = Field(default=None, alias="initiationType")
    language: StrictStr | None = None
    buyer: SercopOrganizationReference | None = None
    parties: list[SercopParty] | None = None
    planning: dict[str, object] | None = None
    tender: SercopTender | None = None
    awards: list[SercopAward] | None = None
    contracts: list[SercopContract] | None = None
    related_processes: list[SercopRelatedProcess] | None = Field(
        default=None, alias="relatedProcesses"
    )


class SercopRecordPackage(_SercopModel):
    """Observed release-package response returned by ``record?ocid=...``."""

    version: StrictStr
    releases: Annotated[list[SercopRelease], Field(min_length=1)]
    uri: StrictStr | None = None
    license: StrictStr | None = None
    publisher: SercopPublisher | None = None
    extensions: list[StrictStr] | None = None
    published_date: StrictStr | None = Field(default=None, alias="publishedDate")
    publication_policy: StrictStr | None = Field(
        default=None, alias="publicationPolicy"
    )
