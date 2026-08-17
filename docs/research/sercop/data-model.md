# Observed SERCOP/OCDS data model

This document describes source data observed on 2026-08-17. It is not a Public
Intelligence domain model.

## Observed package shape

```text
Release package
├── uri
├── version = "1.1"
├── publisher
├── license
├── publicationPolicy
├── publishedDate
├── extensions[]
└── releases[]                 # exactly one in five inspected OCIDs
    ├── ocid
    ├── id
    ├── date
    ├── tag[]
    ├── initiationType
    ├── language
    ├── parties[]
    ├── buyer
    ├── planning?
    ├── tender
    ├── awards[]?
    ├── contracts[]?
    ├── relatedProcesses[]?
    └── extension fields?
```

**Verified — observed:** This differs from the official API documentation's
record-package example. None of the five responses contained `records`,
`compiledRelease`, or `versionedRelease`.

OCDS references used for comparison:

- [Release reference](https://standard.open-contracting.org/latest/en/schema/reference/)
- [Record reference](https://standard.open-contracting.org/latest/en/schema/records_reference/)
- [Codelists](https://standard.open-contracting.org/latest/en/schema/codelists/)
- [Identifiers](https://standard.open-contracting.org/latest/en/schema/identifiers/)

The packages declared OCDS version `1.1`; comparisons used the current OCDS
1.1.5 reference and the extension URLs declared in each package.

## Representative processes inspected

| OCID | Year/type | Release tags | Populated lifecycle sections |
| --- | --- | --- | --- |
| `ocds-5wno2w-SIE-GADMTENA-2026-060-36463` | 2026, Subasta Inversa Electrónica | planning, tender, award, contract, implementation | planning, tender, award, contract; no implementation object |
| `ocds-5wno2w-CPC-GADMCMUISNE-2026-002-38203` | 2026, Concurso publico | planning, tender, award | planning, tender, award |
| `ocds-5wno2w-RE-OACL-GADMSFD-2026-001-2452` | 2026, Obra artística, científica o literaria | planning, tender, award | planning, tender, award |
| `ocds-5wno2w-CE-20260002969199-2455` | 2026, Catálogo electrónico - Compra directa | tender, award, contract | tender, award, contract |
| `ocds-5wno2w-CE-20150000092768-23237` | 2015, Catálogo electrónico - Compra directa | tender, award, contract | tender, award, contract |

## Identifiers

- **Verified — documented:** OCDS defines `ocid` as the globally unique
  contracting-process identifier. Treat it as SERCOP's external process key.
- **Observed:** Search `id` is numeric and distinct from `ocid`.
- **Unknown:** The semantic role and stability of search `id` are not defined
  by the inspected official documentation or saved fixture.
- **Recommendation:** Do not use search `id` as process identity; use the
  documented `ocid` for record lookup and preserve `id` only as an opaque
  source field.
- **Observed:** Release IDs combine tender/process text, a timestamp, and in
  three of five samples a `-compiled` suffix. Preserve them as opaque source
  identifiers.
- **Observed:** Tender IDs resemble the internal process code embedded in the
  OCID. Award and contract IDs have different source-specific forms and
  `contracts[].awardID` cross-references the award.
- **Observed:** Party and primary-identifier values had the form
  `EC-RUC-<13 digits>-<source suffix>`, with scheme `EC-RUC`. The 13-digit
  segment looks extractable in all inspected parties, but the complete value is
  not a bare RUC and must be retained.
- **Observed:** In both catalog samples, `buyer.id` omitted the final source
  suffix and did not exactly match `parties[].id`; `tender.procuringEntity.id`
  did match the party.

**Recommendation:** Preserve complete source identifiers and, in later work,
validate any candidate RUC separately rather than overwriting the source value.

## Organizations

- Buyers were also present in `parties` with roles `buyer` and
  `procuringEntity`.
- Award suppliers were present in `parties` with `supplier`, sometimes also
  `tenderer`.
- Party names, identifier legal names, addresses, and contact points were
  source-provided. Legal entities and natural persons can both appear.
- The inspected samples do not establish cross-process name or identifier
  consistency. Entity resolution remains out of scope.

## Tender, awards, and contracts

Observed tender fields included IDs, titles, descriptions, status, method,
method details, category, value, items, periods, procuring entity, tenderers,
enquiries, lots, and criteria. Presence varied across the inspected records;
the sample does not establish a systematic relationship with procurement type.

Awards linked suppliers and items and usually provided a date and USD value.
Award `status` was null in three current-year samples and `active` in the two
catalog samples.

Contracts referenced awards. Statuses `active` and `terminated` were observed;
contract value, period, and signing date were absent in the catalog samples.
No contract implementation object was observed.

## Money

- All populated currencies observed in the inspected record packages were
  `USD`.
- Tender, planning, award, contract, item-unit, and value-breakdown amounts can
  each occur.
- One process had no tender value but did have item-unit, award, and contract
  values.
- Contract values were null in both catalog samples.
- The bulk CSV award table defined columns for `correctedValue` and
  `enteredValue`; their population was not established by this sample.
- The saved search summaries represented `amount` and `budget` as decimal
  strings and supplied no currency field; their currency is unknown.

Do not infer USD when a currency is absent.

## Dates

Observed dates used ISO-like date-times with `-05:00`; timestamps embedded in
some release IDs used `Z`. Relevant fields included package `publishedDate`,
release `date`, tender/enquiry/award periods, award date, contract signing date,
and contract period.

Dates and periods were nullable. In the 2015 catalog sample, the release date
was in 2015 while package publication and release-ID timestamps were in 2021.
These fields represent different source concepts and must not be collapsed.

## Classifications and items

- `classification.scheme` was `CPC` in inspected items.
- Additional classifications also used `CPC` and could include a SERCOP portal
  product URL.
- Quantities, unit IDs/names, item descriptions, and unit monetary values were
  observed.
- A `SERCOP` unit scheme and CPC codes at different granularities were present.

These fields appear useful for later opportunity matching, but their coverage
and code semantics require a separate implementation specification.

## Statuses and lifecycle history

Observed tender statuses: `active`, `complete`.  
Observed award statuses: `active`, null.  
Observed contract statuses: `active`, `terminated`.

The non-null values are defined by the corresponding OCDS tender, award, and
contract status codelists. Null award status is absence of a value, not a
SERCOP-specific status.

All five OCID responses contained a single, multi-tag release. Three IDs ended
in `-compiled`. No previous states, compiled release object, or versioned
release object was exposed. A release with an `implementation` tag contained no
implementation object.

**Recommendation:** Treat these as source snapshots, not as a trustworthy event
history. An OCDS release remains distinct from a Public Intelligence Event.

## Extensions and links

All inspected packages declared eight extension URLs covering enquiries, lots,
techniques, SERCOP entered values, auctions, value breakdowns, competitive
information, and bids. Observed extension structures included enquiries, lots,
electronic-auction techniques, auctions/bids, and item value breakdowns.

No tender, award, or contract document arrays were populated in the five
samples. Source-related links were observed in package metadata, organization
contact points, additional classifications, and related processes. Document
coverage outside the sample remains unknown.
