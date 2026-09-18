# Supplier identity and award semantics

**Research date:** 2026-09-18

## Source structures

Existing official SERCOP samples and SPEC-002 research expose three related but
non-equivalent representations:

```text
search summary
└── suppliers: display string

award
└── suppliers[]
    ├── id
    └── name

party
├── id
├── name
├── roles[]
└── identifier
    ├── scheme
    ├── id
    └── legalName
```

- **Observed — existing SERCOP samples:** award suppliers also appeared as
  parties with a `supplier` role and sometimes a `tenderer` role.
- **Observed — existing SERCOP samples:** party and identifier values used
  composite forms such as `EC-RUC-<13 digits>-<source suffix>`.
- **Observed — existing SERCOP samples:** references can differ from the full
  party ID; catalog buyer references omitted a source suffix.
- **Unknown:** whether ELECTROLEG uses one stable ID, RUC representation, and
  legal name across the 2025–2026 window.

The complete source identifier must be preserved. A 13-digit segment may be a
candidate RUC only after source-specific validation; it must not replace the
original value.

## Search result to award relationship

The intended verification was:

```text
search summary supplier
        ↓ same OCID
record awards[].suppliers
        ↓ matching ID
parties[] + identifier + roles
```

The known 2018 search result supplied a suitable OCID, but the first live API
request in this execution returned HTTP 429. Following the stop rule, no record
request was made.

- **Observed:** the prior search summary names ELECTROLEG S.A. as supplier.
- **Unknown:** this specific result's supplier string could not be compared
  with its live `awards[].suppliers` and `parties[]` during SPEC-011 execution.
- **Observed — other existing SERCOP fixtures:** normalized procurement
  suppliers are derived from `awards[].suppliers`, not from tenderers or search
  summary strings.
- **Unknown:** official documentation reviewed here does not state that the
  `supplier` search index is exclusively built from award suppliers.

Consequently, targeted supplier results cannot yet be treated as universally
Verified award-supplier activity. The future corpus must classify an award
using the record/package award path itself.

## Identity rule suitable for a future experiment

A defensible bounded rule is:

1. include a process only when an award has a supplier reference;
2. retain the exact award supplier `id` and `name`;
3. link that reference to a party only by an explicit source identifier match;
4. retain the complete party ID and identifier structure;
5. use names for discovery/review, not silent entity reconciliation;
6. report unmatched or conflicting identities rather than guessing.

This is a proposed evidence-selection rule, not entity resolution.

The current normalized domain preserves award supplier `external_id` and
`name`, which is enough to filter exact observed source IDs or exact observed
names after ingestion. It does not preserve identifier scheme, legal name, or
a separately validated RUC.

## Award history versus participation history

| Source evidence | Supported statement | Statements not established |
| --- | --- | --- |
| `awards[].suppliers[]` | Organization is explicitly associated with that source award | Submitted a bid, competed in every stage, supplied under every contract |
| Party role `supplier` linked to an award supplier | Corroborating supplier identity | Award by itself if no award linkage exists |
| Party role `tenderer` or tenderer list | Source represents the party as a tenderer | Award winner or contract supplier |
| Bid structure | Source represents a bid according to that structure | Award unless linked to an award |
| Quotation/proforma/provider list | Organization appears in that published interaction | Bidder, participant, competitor, winner, or awarded supplier |

Award history and participation/proforma history therefore require separate
evidence contracts and may require separate official access mechanisms.

## Commercial field inventory

Availability reflects current code and existing bounded SERCOP evidence, not
dataset-wide completeness.

| Commercial fact | Source path | Current normalized field | Classification |
| --- | --- | --- | --- |
| Process identity | `release.ocid` | `SourceReference.external_id` | Already normalized |
| Evidence pointer | persisted package evidence | `SourceReference.evidence_id` | Already normalized |
| Buyer ID/name | `release.buyer` | `ProcurementRecord.buyer` | Already normalized |
| Tender ID | `tender.id` | `procedure.external_id` | Already normalized |
| Title/description | `tender.title`, `description` | procedure title/description | Already normalized |
| Procedure status | `tender.status` | `procedure.status` | Already normalized |
| Method/type detail | `procurementMethod`, `procurementMethodDetails` | method/method details | Already normalized |
| Main category | `mainProcurementCategory` | `procedure.category` | Already normalized |
| Tender value | `tender.value` | `procedure.value` | Already normalized when present |
| Award ID/status/date/value | `awards[]` | `Award` | Already normalized |
| Award supplier ID/name | `awards[].suppliers[]` | `Award.suppliers` | Already normalized |
| Aggregated award suppliers | derived from awards | `ProcurementRecord.suppliers` | Already normalized |
| Contract ID/award link/status/date/value | `contracts[]` | `Contract` | Already normalized |
| Normalized observation time | database metadata | stored created/updated timestamps | Already normalized; not source procurement date |
| Package publication date | `publishedDate` | none | Raw only |
| Release date/tags/ID | `release.date`, `tag`, `id` | none | Raw only |
| Identifier scheme/value/legal name | `parties[].identifier` | none | Raw only and important for identity |
| Party roles | `parties[].roles` | none | Raw only |
| Procurement periods | tender/enquiry/award/contract periods | none | Raw only |
| CPC/classifications | item classifications | none | Raw only |
| Tender/award/contract items | corresponding `items[]` | none | Raw only |
| Item description/quantity/unit/unit value | item fields | none | Raw only |
| Lots, bids, tenderers | extension/core structures | none | Raw only; semantics vary |
| Value breakdowns | extension fields | none | Raw only |
| Related processes | `relatedProcesses[]` | none | Raw only |
| Documents/source links | document/link fields | none | Raw only; sparse in samples |

## Important limitations

- `ProcurementQueries` supplier search operates on normalized
  procurement-level suppliers aggregated from award suppliers. It does not
  expose which award matched.
- Name substring search is useful for exploration but is not identity
  resolution.
- Exact source IDs can be retained today, but a stable ELECTROLEG ID across the
  target period has not been established.
- Product/category analysis requires a separate bounded item/classification
  normalization spec; SPEC-011 does not implement it.

