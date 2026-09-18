# Supplier award history acquisition recommendation

**Research date:** 2026-09-18  
**Decision:** `HYBRID`

## Decision-rule application

### `TARGETED_API`

Rejected as the acquisition strategy.

- **Verified:** official targeted-search documentation requires both year and
  a keyword of at least three characters.
- **Verified:** no supplier-only targeted operation is documented on the
  reviewed official API page.
- **Observed:** one historical partial-name search found ELECTROLEG S.A.
- **Unknown:** exact name, RUC, source-ID, and award-index semantics.

Arbitrary product keywords create unmeasurable coverage bias, so TARGETED_API
does not satisfy the SPEC-011 completeness rule.

### `BULK`

Bulk is required for corpus acquisition.

- **Verified:** the official page provides JSON by year, month, and method over
  the requested calendar range.
- **Observed:** the existing system successfully handles one small official
  JSON partition.
- **Unknown:** all-type artifact sizes and complete-window operational volume.

Bulk alone could acquire the source corpus, but targeted record access still
has material verification value.

### `HYBRID`

Selected.

```text
official bulk JSON
    → acquisition universe and preserved evidence
    → award-supplier filtering from packages

targeted search/OCID lookup
    → bounded verification and selected source checks only
```

Targeted access must never define the universe or fill gaps through guessed
keywords. It is supplementary and may be unavailable because of throttling.

### `INSUFFICIENT_EVIDENCE`

Not selected for the strategy decision. Evidence is sufficient to rule out
keyword search as complete and to identify official bulk JSON as the corpus
source. Important operational and identity unknowns constrain the next spec,
but they do not require returning to arbitrary-keyword acquisition.

## Qualitative comparison

No numerical scoring model is used.

| Criterion | TARGETED_API | BULK | HYBRID |
| --- | --- | --- | --- |
| Factual correctness | Useful per selected result; supplier semantics incomplete | Award structures available in packages | Bulk award facts plus bounded record verification |
| Coverage | Biased by mandatory keyword | Defines an official partition universe | Bulk defines universe; targeted does not alter it |
| Reproducibility | Query reproducible, result completeness not defensible | Explicit partitions and evidence are reproducible | Reproducible corpus with separately recorded checks |
| Operational safety | Request/page volume and observed 429 are concerns | Bounded explicit downloads; sizes still need validation | Bulk-first with very few optional targeted calls |
| Implementation simplicity | Existing client, but cannot solve completeness | Existing one-partition pipeline is reusable | Smallest defensible composition of existing boundaries |
| ELECTROLEG usefulness | Good for known-case checks | Necessary for finding awards without known keywords | Best fit once bounded bulk feasibility is confirmed |

## Proposed next specification

### SPEC-012 — Bounded Supplier Award Corpus Ingestion

**Goal:** Given a human-reviewed explicit manifest of official SERCOP bulk
partitions, preserve their evidence, normalize their procurement snapshots, and
produce a factual award-supplier corpus that can be filtered by exact observed
source identifiers and names.

The first phase should:

1. validate one representative monthly `method=all` JSON artifact;
2. record count, byte size, archive shape, and memory implications;
3. prove award-supplier extraction using `awards[].suppliers`;
4. preserve complete source IDs and report unmatched/ambiguous party links;
5. process only an explicit approved manifest;
6. expose a run summary and failures without scheduling or automatic range
   expansion;
7. allow targeted OCID verification as an optional manual research step, not a
   coverage mechanism.

If the all-type proof is too large or structurally incompatible, SPEC-012
should stop and require a revised explicit specific-type manifest rather than
silently introducing concurrency, streaming infrastructure, or automatic
backfill.

## Explicit exclusions for SPEC-012

- automatic 21-month backfill;
- scheduler or background workers;
- concurrent downloads;
- generic retry infrastructure;
- entity resolution or canonical company profiles;
- CPC/item normalization;
- participation/proforma ingestion;
- signals, opportunities, scoring, rankings, or dashboards;
- AI/LLM functionality.

Product and CPC/item normalization should be a later bounded spec because the
current normalized model deliberately omits those raw structures.

## Future access behavior

Any later targeted implementation should:

- respect `Retry-After` when supplied;
- use only a small bounded retry policy justified by a separate accepted spec;
- avoid concurrency by default;
- expose an explicit failure after the bounded policy;
- preserve rate-limit response metadata as operational evidence;
- never attempt to discover the threshold.

Bulk execution should similarly remain sequential until measured artifact
sizes and source guidance justify another approach.

## Remaining unknowns that block broader claims

- Search supplier → award supplier semantics for ELECTROLEG.
- Exact-name, RUC, and source-ID targeted matching.
- A stable ELECTROLEG identifier across the target period.
- `method=all` composition and parser compatibility.
- Monthly counts, artifact sizes, and memory requirements.
- Partition overlap and republishing behavior.
- Completeness of the current September 2026 partition.
- Rate-limit window and accounting policy.
- Official access for participation/proforma history.

Until those questions are resolved, any resulting profile must be described as
an observable award history over the explicitly successful source partitions,
not as all commercial activity by ELECTROLEG.

