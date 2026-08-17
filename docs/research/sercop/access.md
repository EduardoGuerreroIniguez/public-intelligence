# SERCOP access profile

## Official sources inspected

All sources were accessed on 2026-08-17.

| Source | Purpose |
| --- | --- |
| [Contrataciones Abiertas Ecuador](https://datosabiertos.compraspublicas.gob.ec/PLATAFORMA) | Official public OCDS platform |
| [API documentation](https://datosabiertos.compraspublicas.gob.ec/PLATAFORMA/datos-abiertos/api) | Search and OCID lookup contract |
| [Bulk downloads](https://datosabiertos.compraspublicas.gob.ec/PLATAFORMA/datos-abiertos) | Year/month/procurement-type downloads |
| [About](https://datosabiertos.compraspublicas.gob.ec/PLATAFORMA/acerca) | Access terms and responsibility for source data |
| [Methodological notes](https://datosabiertos.compraspublicas.gob.ec/PLATAFORMA/notas-metodologicas) | Source systems, transformations, mappings, and refresh behavior |
| [Publication policy](https://datosabiertos.compraspublicas.gob.ec/PLATAFORMA/documentos/politica-publicacion-SERCOP-OCDS.pdf) | Publication scope and access mechanisms |

The SERCOP pages reported an update date of 2026-08-16 during the original
research. The About page was rechecked on 2026-08-17 and then reported an
update date of 2026-08-17.

## Publication and access terms

- **Verified — documented (2026-08-17):** The official
  [About](https://datosabiertos.compraspublicas.gob.ec/PLATAFORMA/acerca) page
  states that the procurement open data is freely accessible and has no usage
  restrictions. It also states that contracting entities and suppliers are
  responsible for the truthfulness, accuracy, consistency, and currency of
  information they enter in SOCE.
- **Verified — observed (2026-08-17):** All three saved responses from the
  official `GET /api/record` endpoint declare
  `https://creativecommons.org/licenses/by/3.0/ec/`, the Creative Commons
  Attribution 3.0 Ecuador license, in their top-level `license` field. They
  also link the official SERCOP publication policy through
  `publicationPolicy`.
- **Unknown:** This research does not establish a legal interpretation of the
  About page's unrestricted-use statement relative to the attribution
  condition in the package license. Future use should retain provenance and
  comply with the license declared in each source package.

These terms apply to the public open-data publication. They do not authorize
access to authenticated SOCE functionality or circumvention of technical
controls.

## Mechanism comparison

| Mechanism | Authentication | Shape | Pagination/filtering | Best fit |
| --- | --- | --- | --- | --- |
| `GET /api/search_ocds` | None required in observed requests | SERCOP-specific summaries | `year`, `search`, `page`, `buyer`, `supplier`; 10 rows per observed page | Discovery and targeted candidate selection |
| `GET /api/record?ocid=...` | None required in observed requests | OCDS 1.1 release package with one observed release | Exact OCID; no pagination | Targeted source snapshot |
| `GET /get-totals` | None required in observed request | `{"count": n}` | `year`, `month`, `method` | Bulk partition sizing through official UI |
| `GET /download` | None required in observed requests | ZIP for JSON/CSV; XLSX file | `type`, `year`, `month`, `method` | Historical/batch acquisition candidate |

No API key, login, or authentication challenge appeared in documentation or
observed requests. This is evidence only for the public endpoints tested; it
does not authorize access to authenticated SOCE functionality.

## Keyword search

The documentation marks `year` and `search` as required, with `search` at
least three characters and coverage from 2015 through the current year.

Observed successful requests:

| Query | HTTP | Total | Page/pages | Result |
| --- | ---: | ---: | --- | --- |
| `year=2026&search=agua&page=1` | 200 | 1,133 | 1/114 | Ten summaries |
| `year=2026&search=agua&page=2` | 200 | 1,133 | 2/114 | Next ten summaries |
| `year=2015&search=agua&page=1` | 200 | 3,515 | 1/352 | Ten summaries |
| `year=2026` without `search` | 200 | 82,540 | 1/8,254 | Ten summaries |

**Verified — observed:** Pagination uses response fields `total`, `page`, and
`pages`; page 2 returned different OCIDs. Search results are summaries, not
OCDS releases or records.

Observed summary fields were:

```text
id, ocid, year, month, method, internal_type, locality, region,
suppliers, buyer, amount, date, title, description, budget
```

The saved 2015 page contained ten summaries. Every field was non-null in that
fixture and had the following observed representation:

| Field(s) | Observed JSON type and meaning |
| --- | --- |
| `id` | Number (integer); distinct from `ocid`. Its semantic role and stability are unknown. |
| `ocid` | String; the contracting-process identifier used for record lookup. |
| `year`, `month` | Numbers (integers). |
| `amount`, `budget` | Decimal-formatted strings, for example `"24.200000"` and `"24.2"`; no currency field accompanies them. |
| `buyer`, `suppliers` | Strings containing names, not organization identifiers or party objects. |
| `method`, `internal_type`, `locality`, `region`, `title`, `description` | Strings. |
| `date` | String containing a date-time with an observed `-05:00` offset. |

The search summary therefore does not provide enough information to attach a
currency to `amount` or `budget`, or to identify buyer and supplier entities
beyond their source-provided names. Full-record money and party semantics must
not be applied to these fields. Other inspected search pages contained nulls,
so the non-null saved fixture does not establish required-field guarantees.

**Observed discrepancy:** The current documentation example uses fields such
as `buyerId`, `buyerName`, and `single_provider`, while live responses used
`buyer` and `suppliers` and added other fields. The future connector must treat
the live source contract as source-specific and fixture-test it.

**Observed discrepancy:** Omitting the documented-required `search` parameter
returned an unfiltered result set rather than a validation error. A connector
should still send documented parameters and must not rely on this behavior.

## OCID lookup

Five real OCIDs returned HTTP 200 and `application/json`. An unknown OCID
returned HTTP 404 with an HTML `Not Found` page, not a JSON error contract.

The official example shows a top-level `records` array. Every inspected live
response instead contained:

```text
uri, license, version, releases, publisher, extensions,
publishedDate, publicationPolicy
```

Each package contained exactly one embedded release. No `records`,
`compiledRelease`, or `versionedRelease` was observed.

## Authentication, rate limits, and errors

- **Verified — observed:** Requests without credentials succeeded.
- **Verified — observed:** API responses included `X-RateLimit-Limit: 60` and
  `X-RateLimit-Remaining`.
- **Unknown:** The reset window, identity used for accounting, documented
  quotas, and throttling response contract.
- **Observed:** Remaining counts were not monotonic across sequential calls,
  so they cannot be interpreted as a simple process-wide budget.
- **Observed:** Unknown OCIDs produce an HTML 404. Missing `search` does not
  produce an error.

No load test or repeated throttling attempt was performed.

## Historical coverage

- **Verified — documented:** Search and bulk UI coverage begins in January
  2015 and extends through the current year/month.
- **Verified — observed:** Search and record requests succeeded for 2015 and
  2026.
- **Unknown:** Whether every month/type partition is complete or whether older
  records are republished after source corrections.

## Bulk downloads

The official page constructs:

```text
/download?type=<json|csv|xlsx>&year=<year>&month=<month>&method=<method>
```

It also calls `/get-totals` with the same partition dimensions. A 2026-07
`Obra artística, científica o literaria` partition reported three procedures.

| Format | HTTP metadata | Inspected shape |
| --- | --- | --- |
| JSON | ZIP, 3,119 bytes | One JSON member, 16,640 bytes; array of three release packages |
| CSV | ZIP, 4,883 bytes | Eight CSV members: metadata, extensions, releases, planning, tender, awards, suppliers, contracts |
| XLSX | XLSX, 19,216 bytes | Eight analogous worksheets: Metadata, Extensions, Releases, Planning, Tender, Awards, AwardSuppliers, Contracts |

The JSON packages retained nested parties, items, and extensions. The tabular
formats flattened selected sections and did not expose equivalent tables for
all nested structures observed in JSON, such as items, enquiries, lots, and
auctions. JSON is therefore the stronger candidate for lossless future
ingestion.

Downloaded bulk artifacts were inspected but not committed because the small
partition included natural-person supplier data. Their request metadata and
hashes are recorded in [samples/README.md](samples/README.md). No partial or
HTTP Range sample was created.
