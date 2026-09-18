# SERCOP supplier award history research

**Research date:** 2026-09-18  
**Spec:** [SPEC-011](../../../specs/SPEC-011-sercop-supplier-award-history-access-research.md)  
**Subject:** ELECTROLEG S.A.  
**Candidate window:** 2025-01-01 through 2026-09-18

## Question

This research asks how Public Intelligence can construct a defensible,
reproducible history of SERCOP procurement awards associated with one supplier.
It does not construct that history or infer participation, competition, or
commercial opportunity.

## Evidence labels

- **Verified:** supported by current official documentation or unambiguous
  authoritative source evidence.
- **Observed:** present in an identified request, response, or bounded sample,
  without claiming a general source guarantee.
- **Unknown:** not established by the available evidence.

Every material conclusion in this research uses one of these labels. An
undocumented behavior is not upgraded from Observed to Verified merely because
it is repeatable or convenient.

## Executive findings

- **Verified — official documentation, 2026-09-18:** `search_ocds` supports
  keyword search and documents both `year` and `search` as required. `search`
  must contain at least three characters. `supplier` is optional and described
  only as a keyword for locating a particular supplier.
- **Verified — official documentation, 2026-09-18:** the documented targeted
  API offers keyword search and exact OCID lookup. The reviewed documentation
  does not provide a supplier-only operation.
- **Observed — prior bounded request documented by SPEC-011:**
  `year=2018`, `search=accesorios`, `supplier=ELECTROLEG` returned one summary
  naming `ELECTROLEG S.A.` and OCID
  `ocds-5wno2w-SIE-EEASA-002-2018-3233`. This supports partial-name matching in
  that case only.
- **Unknown:** exact-name, RUC, complete source-ID, and dataset-wide supplier
  matching semantics could not be established.
- **Unknown:** the 2018 search result could not be re-fetched and compared with
  `awards[].suppliers` during this session because the first API probe returned
  HTTP 429.
- **Observed — live, 2026-09-18:** the first and only API probe returned
  `429 Too Many Requests`, `X-RateLimit-Limit: 60`,
  `X-RateLimit-Remaining: 0`, `Retry-After: 28`, and
  `X-RateLimit-Reset: 1789747282` (`2026-09-18T16:01:22Z`). Research traffic
  stopped immediately; the throttling threshold was not tested.
- **Verified — official public bulk page, 2026-09-18:** bulk data is offered by
  year, month, and procurement type in JSON, CSV, and XLSX. The page currently
  advertises coverage from 2015-01 through 2026-09, lists 27 specific
  procurement types, and includes an `all` type option.
- **Observed — existing SPEC-002 evidence:** one small JSON bulk partition was
  a ZIP containing an array of three release packages and was successfully
  suitable for the current bounded bulk implementation.
- **Unknown:** current counts, artifact sizes, republishing behavior, and
  buffered-processing suitability for the 2025–2026 all-type partitions were
  not probed after the access restriction.

## Documentation execution boundary

The current official API documentation and public bulk-download page were
successfully retrieved before the access restriction. A fresh retrieval of the
About page, methodological notes, publication-policy PDF, and OCDS reference
was not attempted afterward. Their findings from SPEC-002 (2026-08-17) were
reused only where identified as existing evidence; they were not represented as
new 2026-09-18 verification. This avoided further source traffic after the 429
and does not affect the documented mandatory-keyword or bulk-partition
conclusions established directly by the two current pages.

## Decision

**HYBRID** is recommended.

Bulk JSON is required for the acquisition universe because the officially
documented targeted API requires an arbitrary keyword. Targeted search and
record-by-OCID remain useful only for bounded verification, source-shape checks,
and investigation of selected records. Targeted results must not define the
historical universe.

This decision follows the SPEC-011 rules before considering implementation
convenience. See [recommendation.md](recommendation.md).

## Scope of “award history”

The intended corpus contains processes in which source evidence explicitly
associates the target organization with `awards[].suppliers`. It does not
automatically include tenderers, quotations, proformas, bids, market-study
respondents, or every commercial interaction with a public institution.

“Complete” must always be qualified by source, publication coverage, time
window, successfully processed partitions, and the identity rule used.

## Research artifacts

- [Targeted access and rate-limit evidence](targeted-access.md)
- [Supplier identity, award semantics, and field inventory](supplier-identity.md)
- [Bulk feasibility](bulk-feasibility.md)
- [Strategy recommendation](recommendation.md)

## Principal unresolved questions

- Whether `supplier` searches award suppliers specifically or another indexed
  supplier representation.
- Exact-name, RUC, and complete source-ID matching behavior.
- Whether ELECTROLEG uses one stable source identifier and spelling throughout
  the target period.
- The size and supported shape of monthly `method=all` artifacts.
- Whether monthly/type partitions overlap or are republished after corrections.
- The completeness of September 2026 while it is still the current month.
- The rate-limit window, accounting identity, and operational policy.
- How participation/proforma history can be obtained from a separately
  supported public source, if commercially required.
