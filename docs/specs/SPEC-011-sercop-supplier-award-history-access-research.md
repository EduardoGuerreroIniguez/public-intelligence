# SPEC-011 — SERCOP Supplier Award History Access Research

**Status:** Implemented
**Milestone:** 3 — Commercial Intelligence Validation
**Type:** Research / Discovery
**Depends on:** SPEC-002 through SPEC-010
**Date drafted:** 2026-09-18

---

## 1. Context

Public Intelligence can currently:

* access SERCOP through the targeted OCDS connector;
* search contracting processes by keyword;
* filter targeted searches by buyer or supplier;
* retrieve one process by OCID;
* ingest one explicit historical bulk partition;
* preserve raw evidence and provenance;
* map SERCOP data into source-independent procurement facts;
* persist normalized procurement snapshots;
* query normalized procurements;
* explore normalized data through a minimal web interface.

The project is now being exercised against its first concrete commercial-intelligence use case:

> understand the observable public-procurement activity of a real supplier and use that evidence to support commercial analysis.

The initial research subject is **ELECTROLEG S.A.**

### Prior live observations

Before this spec, bounded manual probes against the public SERCOP API produced
the following observations.

Positive control:

```text
year=2018
search=accesorios
supplier=ELECTROLEG

total=1

OCID=ocds-5wno2w-SIE-EEASA-002-2018-3233
buyer=EMPRESA ELECTRICA AMBATO REGIONAL CENTRO NORTE S.A.
supplier=ELECTROLEG S.A.
amount=82097.680000
```

Selected current-period probes:

```text
year=2025
search=interruptor
supplier=ELECTROLEG
total=0
```

```text
year=2026
search=medidor
supplier=ELECTROLEG
total=0
```

```text
year=2026
search=energia
supplier=ELECTROLEG
total=0
```

Control searches without a supplier filter returned:

```text
2025 + interruptor -> 7 results
2026 + medidor     -> 137 results / 14 pages
```

Repeated live requests also produced an HTTP 429 response.

Live source responses additionally demonstrated that fields such as
`locality` and `region` may be null even in successful search responses.

These are observations only. They are not treated as general SERCOP guarantees.

These observations demonstrate that the current connector is useful for
targeted verification, but they do not establish a reliable mechanism for
reconstructing a supplier's complete award history.

This spec exists to resolve that uncertainty before introducing a
supplier-award-history ingestion feature.

---

## 2. Problem

A commercial-intelligence workflow needs to answer questions such as:

```text
¿A qué instituciones ha vendido este proveedor?
¿Qué adjudicaciones públicas observables ha recibido?
¿Qué productos o categorías aparecen en esas adjudicaciones?
¿Cuánto se le ha adjudicado?
¿Con qué frecuencia compra cada entidad?
¿Cómo ha cambiado esa actividad en el tiempo?
```

The current targeted API cannot simply express:

```text
all procurements for supplier X
```

because the documented keyword-search operation also requires a search term.

Using arbitrary keywords such as:

```text
interruptor
medidor
energía
cable
```

would create an unknown and potentially severe coverage bias.

Conversely, the existing bulk mechanism is intended for historical corpus
construction, but currently operates one explicit:

```text
year + month + procurement type
```

partition at a time.

Before implementing automated supplier-award-history construction, the project
must determine which official public-data mechanism provides the most correct,
reproducible, responsible, and maintainable path.

---

## 3. Goal

Produce an evidence-based recommendation for reconstructing the
**observable awarded-procurement history of a supplier** from SERCOP public
data.

At completion, the repository should be able to answer:

1. What exactly does the SERCOP `supplier` search filter represent?
2. Does it identify award suppliers, another supplier concept, or different semantics depending on procurement type?
3. Does supplier search use substring, exact name, normalized name, identifier, or another matching mechanism?
4. Can a RUC or source organization identifier be used directly?
5. Can the targeted API retrieve a supplier's complete award history without introducing arbitrary keywords?
6. Is there another currently documented official endpoint or query mechanism for supplier-oriented record access?
7. If not, is bulk OCDS ingestion the preferred source for complete supplier-award-history reconstruction?
8. How should available bulk partitions be discovered safely and reproducibly?
9. What bounded historical range is appropriate for the first commercial experiment?
10. How should HTTP throttling and `429` behavior influence future implementation?
11. Which SERCOP facts are sufficient to classify a process as an award to the target supplier?
12. Which observable supplier activities are **not** represented by award-supplier data?
13. What should the next implementation spec build?

The output of SPEC-011 is research and a bounded implementation recommendation.

It does **not** implement the supplier-award-history pipeline.

---

## 4. Primary use case

The first practical consumer of this research is the ELECTROLEG
commercial-intelligence experiment.

Initial analysis window:

```text
2025-01-01
through
2026-09-18
```

Historical cases outside that range may be used as controls when useful.

The known 2018 ELECTROLEG award may be used as a positive control for
supplier-search semantics.

The research must not assume that ELECTROLEG's observed behavior generalizes
to every supplier or procurement method.

---

## 5. Terminology

### Award supplier

An organization explicitly associated by the source with a procurement award.

Conceptually:

```text
award
  └── suppliers[]
```

This is factual source data.

### Search supplier

The meaning of the `supplier` parameter exposed by SERCOP's targeted-search
interface.

Its exact relationship to award suppliers must be verified by this research.

### Observable supplier award history

The set of contracting processes in the chosen source coverage where the
available evidence explicitly associates the target organization with an
award.

It is not necessarily equivalent to:

* every commercial interaction with a public institution;
* every submitted offer;
* every quotation;
* every proforma;
* every tender participation;
* every market-study response.

### Observable participation

Evidence that a supplier appeared in another public-procurement interaction,
such as a published proforma/provider list.

This is outside the meaning of `award history` unless the source explicitly
links that organization to an award.

### Complete

Within this research, `complete` must always be scoped to an explicitly
documented source, period, and data coverage.

Do not use the term to imply knowledge of private or unpublished procurement
activity.

---

## 6. Research questions

### RQ-1 — Supplier filter semantics

Using a small number of controlled requests, determine what `supplier`
matches.

Test, where source availability permits:

```text
ELECTROLEG
ELECTROLEG S.A.
known supplier identifier/RUC
```

Use at least one known positive award as a control.

Document:

* returned supplier value;
* exact/legal-name matching;
* partial-name matching;
* whether suffixes such as `S.A.` matter;
* whether identifier/RUC matching works;
* inconsistencies between procurement types, if observed.

Do not stress-test the service.

---

### RQ-2 — Relationship to awards

For successful supplier-filter results:

1. retrieve representative records by OCID;
2. inspect `awards[].suppliers`;
3. inspect relevant `parties[]` and roles;
4. compare those structures with the supplier value returned by search.

Determine whether the available evidence supports treating targeted supplier
results as awarded-supplier activity.

Classify conclusions as:

* Verified;
* Observed;
* Unknown.

Do not infer participation or bid submission merely from award-supplier
evidence.

---

### RQ-3 — Supplier identity

Investigate the strongest available supplier identity.

Inspect:

```text
organization name
party id
identifier.scheme
identifier.id
identifier.legalName
award supplier id
award supplier name
```

Determine whether Ecuadorian RUC is consistently recoverable from
representative awarded-supplier records.

Answer:

```text
Can supplier award history eventually be keyed by a stable source identifier?
```

Do not implement entity resolution.

---

### RQ-4 — Targeted API completeness

Evaluate whether `search_ocds` can retrieve all awards associated with a
supplier without introducing product or description keywords.

Specifically investigate whether:

* `search` can be omitted;
* a neutral/wildcard search is documented;
* an empty search is supported;
* current official public SERCOP documentation exposes another supplier-oriented access mechanism;
* another publicly documented open-data mechanism supports supplier filtering without an arbitrary keyword.

Do not infer a production contract from undocumented browser behavior,
internal endpoints, or authenticated SOCE functionality.

Do not:

* exploit undocumented private endpoints;
* reverse-engineer authenticated SOCE functionality;
* bypass normal validation;
* use wildcard tricks simply to evade the source contract.

If no supported complete supplier query exists, document that clearly.

---

### RQ-5 — Official alternative access mechanisms

Review current official SERCOP open-data documentation for mechanisms relevant
to supplier award history.

At minimum inspect:

1. keyword-search API;
2. OCID record API;
3. official public OCDS access mechanisms;
4. bulk JSON downloads;
5. official publication-policy documentation where accessible.

For every discovered mechanism document:

* whether it is currently documented;
* required parameters;
* pagination;
* supplier filtering;
* historical coverage;
* response structure;
* suitability for repeatable research;
* source restrictions or uncertainties.

A mechanism mentioned in historical documentation but not verifiably exposed
today must not be treated as a production contract.

---

### RQ-6 — Bulk corpus feasibility

Evaluate bulk JSON as the fallback/preferred mechanism for supplier-award-
history reconstruction.

Document:

```text
year
month
procurement type
```

partitioning requirements.

Determine:

* how procurement types available for a year/month can be discovered;
* whether partition discovery itself has a public documented mechanism;
* how many partitions the proposed ELECTROLEG window would require;
* whether existing SPEC-005/SPEC-008 components can process them without redesign;
* whether sequential execution is sufficient for the first experiment;
* whether currently buffered artifact processing is adequate for observed partition sizes used in the experiment.

Do not implement automatic backfill.

---

### RQ-7 — Supplier filtering after bulk normalization

Determine whether the normalized representation created by the existing mapper
contains sufficient award-supplier identity to filter ELECTROLEG reliably after
bulk ingestion.

Evaluate:

```text
ProcurementRecord
    awards[]
        suppliers[]
```

and the aggregated procurement supplier representation.

Determine whether supplier name alone is adequate for the experiment or
whether source organization identifier persistence must be strengthened first.

Do not implement entity resolution.

---

### RQ-8 — Coverage window

Recommend the smallest useful historical corpus for the first commercial
validation.

Default candidate:

```text
2025-01-01 through 2026-09-18
```

Evaluate whether extending farther back materially improves:

* buyer-history analysis;
* recurring customer detection;
* product/category discovery;
* competitor discovery.

Do not choose a larger range merely because data is available.

---

### RQ-9 — Rate limiting and responsible access

Document the observed `HTTP 429` behavior.

Investigate, using normal successful/failed responses only:

* whether `Retry-After` is supplied;
* whether any official rate limit is documented;
* whether the source exposes other relevant throttling headers.

Do not measure the limit by deliberately increasing request frequency.

If exact limits are not documented, classify them as `Unknown`.

Recommend future behavior such as:

```text
429
 ↓
respect Retry-After when supplied
 ↓
bounded retry/backoff
 ↓
explicit failure
```

without implementing it in this research spec.

---

### RQ-10 — Award history versus participation history

Document explicitly what the OCDS award path does **not** establish.

Compare, conceptually and using only a very small number of already-known
public examples where useful:

```text
awarded supplier
```

versus:

```text
provider appearing in public quotation/proforma information
```

Determine whether these require separate source-access mechanisms.

The research must prevent future analytics from labeling a proforma provider
as:

* bidder;
* participant;
* competitor;
* winner;

unless the corresponding evidence supports that label.

---

### RQ-11 — Commercial-analysis fields

Determine which currently available factual fields can support the first
supplier profile.

At minimum evaluate availability of:

* OCID;
* procurement date;
* buyer name and identifier;
* award supplier name and identifier;
* tender title;
* tender description;
* procurement method/type;
* tender value;
* award value;
* contract value;
* award date;
* classification/CPC;
* tender items;
* award items;
* quantities;
* units.

Classify each as:

```text
Already normalized
Available in raw SERCOP but not normalized
Unavailable/not observed
```

This question should directly inform the later product/classification spec.

---

## 7. Candidate strategies to compare

The research must compare at least these strategies.

### Strategy A — Targeted supplier search

```text
search_ocds
+
supplier
```

Potential advantage:

* small and interactive.

Known concern:

* mandatory keyword may make coverage incomplete.

---

### Strategy B — Bulk historical corpus

```text
bulk partitions
      ↓
raw evidence
      ↓
existing mapper
      ↓
normalized PostgreSQL
      ↓
supplier filtering
```

Potential advantage:

* appropriate foundation for reproducible historical analytics.

Known concerns:

* partition enumeration;
* ingestion volume;
* supplier identity quality;
* currently bounded one-partition workflow.

---

### Strategy C — Another official supplier-oriented mechanism

Use only if current official public documentation and successful bounded
testing establish one.

Do not rely on undocumented endpoints simply because they can be discovered in
browser traffic or historical references.

---

## 8. Research methodology

### Step 1 — Read project context

Read:

* `AGENTS.md`
* `docs/vision.md`
* relevant ADRs
* `SPEC-002`
* `SPEC-003`
* `SPEC-005`
* `SPEC-006`
* `SPEC-008`
* `SPEC-009`
* `SPEC-010`

Inspect existing SERCOP connector, domain, persistence, and pipeline code before
recommending changes.

---

### Step 2 — Review existing SERCOP research

Reuse existing `docs/research/sercop/` evidence.

Do not redo SPEC-002 wholesale.

Document what has changed or what SPEC-011 specifically adds.

---

### Step 3 — Inspect current official documentation

Use current official SERCOP open-data documentation as the authoritative source
for supported SERCOP mechanisms.

Use OCDS documentation only for generic standard semantics.

Record research date because the external service can change.

---

### Step 4 — Execute bounded live probes

Use only a small number of deliberate requests.

Suggested controls:

```text
Known positive:
2018 ELECTROLEG award

Current-period probes:
selected 2025/2026 searches already identified during manual validation
```

Avoid broad automated iteration.

Stop repeated requests if the service returns throttling or availability
errors.

Live source probes are research operations and must not become default test
suite behavior.

Do not add live SERCOP requests under `tests/`.

If a temporary manual probe is needed, keep it outside the default automated
test paths and do not turn it into production tooling unless a later accepted
spec requires it.

---

### Step 5 — Inspect representative records

For a small number of successful OCIDs, inspect enough raw source structure to
answer supplier identity and award-semantics questions.

Do not download unrelated documents.

---

### Step 6 — Evaluate existing bulk capability

Review the existing implementation rather than immediately changing it.

Estimate the bounded work required to create the ELECTROLEG 2025–2026 corpus.

---

### Step 7 — Produce decision

Recommend one of:

```text
TARGETED_API
BULK
HYBRID
INSUFFICIENT_EVIDENCE
```

### Decision rules

Recommend `TARGETED_API` only if current official evidence establishes a
supported supplier-oriented query capable of reconstructing the requested
history without arbitrary keyword selection.

Recommend `BULK` if complete historical coverage requires processing official
bulk partitions and targeted access adds no material acquisition capability.

Recommend `HYBRID` if bulk data is required to build the historical corpus but
targeted API access remains useful for bounded verification, enrichment, or
source validation.

Recommend `INSUFFICIENT_EVIDENCE` if source behavior or current documentation
is not sufficient to justify one of the above strategies safely.

Explain the decision using:

1. factual correctness;
2. coverage;
3. reproducibility;
4. source responsibility;
5. implementation simplicity;
6. usefulness for the immediate ELECTROLEG experiment.

---

## 9. Expected research artifacts

Create a bounded research area:

```text
docs/research/sercop/supplier-history/
├── README.md
├── targeted-access.md
├── supplier-identity.md
├── bulk-feasibility.md
└── recommendation.md
```

Do not create a large new hierarchy if existing research organization makes a
smaller structure clearer.

### `README.md`

Summarize:

* question;
* research date;
* target supplier;
* key observations;
* conclusion;
* unresolved questions.

### `targeted-access.md`

Document:

* `search_ocds` supplier semantics;
* positive/negative controls;
* name matching;
* identifier/RUC behavior;
* completeness limitations;
* observed `429` behavior.

### `supplier-identity.md`

Document:

* supplier identity structures;
* award relationship;
* RUC/source ID evidence;
* name consistency;
* limitations.

### `bulk-feasibility.md`

Document:

* required partitions;
* partition-discovery mechanism;
* estimated bounded corpus;
* reuse of SPEC-005/SPEC-008;
* operational concerns.

### `recommendation.md`

State the preferred implementation strategy and proposed scope for the next
implementation spec.

---

## 10. Evidence classification

Every material research conclusion must use one of:

### Verified

Supported by current official documentation or otherwise established by
unambiguous authoritative source evidence.

### Observed

Observed in one or more live/source samples but not established as a general
source guarantee.

### Unknown

Insufficient evidence.

Do not upgrade:

```text
Observed -> Verified
```

merely because an observation is convenient for the desired implementation.

---

## 11. Non-goals

SPEC-011 does **not** implement:

* automated supplier-award-history ingestion;
* automatic historical backfill;
* scheduled ingestion;
* background workers;
* concurrent bulk downloads;
* retry infrastructure;
* supplier/entity resolution;
* commercial scoring;
* opportunity scoring;
* Bid/No-Bid logic;
* competitor rankings;
* participation inference;
* proforma scraping;
* CPC normalization;
* product clustering;
* item persistence changes;
* new dashboards;
* alerts;
* AI/LLM analysis;
* vector search;
* natural-language querying;
* additional external data sources.

Do not modify production behavior merely to make the research easier.

---

## 12. Technical constraints

* Follow `AGENTS.md`.
* Follow applicable ADRs.
* Do not modify production application behavior.
* Do not add runtime dependencies.
* Do not add development dependencies solely for this research.
* Reuse existing research and connector capabilities where possible.
* Keep research artifacts outside `src/`.
* Do not introduce domain entities.
* Do not implement persistence changes.
* Do not introduce generic ingestion abstractions.
* Do not introduce retry, scheduling, concurrency, or caching infrastructure.
* Do not infer undocumented guarantees from bounded samples.
* Distinguish Verified, Observed, and Unknown findings.
* Default automated tests must not call live SERCOP services.

---

## 13. Source ethics and operational safety

Use only public SERCOP functionality intended for public/open-data access.

Do not:

* bypass authentication;
* bypass CAPTCHA;
* circumvent rate limits;
* scrape authenticated SOCE screens;
* probe private/internal endpoints;
* create unnecessary request volume.

If SERCOP returns `429`:

1. stop repeated requests;
2. preserve the observation;
3. inspect available response metadata;
4. resume only through normal responsible usage;
5. do not attempt to discover the threshold through load testing.

---

## 14. Acceptance criteria

### Research artifacts

* [ ] `docs/research/sercop/supplier-history/README.md` exists.
* [ ] `targeted-access.md` documents targeted supplier-access evidence.
* [ ] `supplier-identity.md` documents observed identity semantics.
* [ ] `bulk-feasibility.md` documents the bounded historical-corpus option.
* [ ] `recommendation.md` records the final strategy decision.
* [ ] Material conclusions are classified as Verified, Observed, or Unknown.

### Targeted supplier access

* [ ] Current official targeted-search documentation has been reviewed.
* [ ] Mandatory and optional search parameters are documented.
* [ ] A known positive ELECTROLEG award is used as a supplier-filter control.
* [ ] Exact/legal-name supplier matching is documented as Verified, Observed, or Unknown.
* [ ] Partial-name supplier matching is documented as Verified, Observed, or Unknown.
* [ ] Supplier matching by RUC/source identifier is documented as Verified, Observed, or Unknown.
* [ ] The relationship between search supplier results and `awards[].suppliers` is evaluated.
* [ ] Targeted API completeness for supplier award history is explicitly concluded.

### Supplier identity

* [ ] Supplier names are inspected.
* [ ] Source organization IDs are inspected.
* [ ] Identifier scheme/value are inspected where present.
* [ ] RUC availability is documented.
* [ ] Name/identifier inconsistencies are documented when observed.
* [ ] No entity-resolution logic is implemented.

### Bulk feasibility

* [ ] Current bulk-download mechanism is revalidated.
* [ ] Partition dimensions are documented.
* [ ] Partition discovery is investigated.
* [ ] Expected work for the 2025–2026 ELECTROLEG corpus is estimated.
* [ ] Existing SPEC-005/SPEC-008 reuse is evaluated.
* [ ] No automatic full-history ingestion is implemented.

### Access behavior

* [ ] Observed HTTP `429` behavior is documented.
* [ ] `Retry-After`/rate-limit metadata is recorded as present, absent, or unknown.
* [ ] No deliberate rate-limit testing is performed.
* [ ] Recommended future handling is documented without implementing a retry framework.
* [ ] No live SERCOP request is added to the default automated test suite.

### Commercial semantics

* [ ] Award history is distinguished from participation/proforma history.
* [ ] No proforma-provider evidence is automatically labeled as award, bidder, participant, or competitor.
* [ ] Fields useful for the supplier commercial profile are inventoried.
* [ ] Fields requiring future normalization, especially classifications/items, are identified.

### Recommendation

* [ ] `recommendation.md` selects `TARGETED_API`, `BULK`, `HYBRID`, or `INSUFFICIENT_EVIDENCE`.
* [ ] The decision follows the explicit decision rules in this spec.
* [ ] Recommendation is justified by coverage, correctness, reproducibility, operational safety, and implementation cost.
* [ ] The first implementation scope is bounded.
* [ ] Remaining unknowns are explicit.
* [ ] A proposed title and goal for the next implementation SPEC are provided.

### Scope and quality

* [ ] No production connector behavior is changed.
* [ ] No database migration is added.
* [ ] No new dependency is added.
* [ ] No scheduler/background worker is introduced.
* [ ] No signals/opportunities are implemented.
* [ ] No CPC/item normalization is implemented.
* [ ] No unrelated refactor is performed.
* [ ] Existing quality checks continue to pass if repository documentation/sample files are added.
* [ ] `git diff --check` passes.

---

## 15. Success criteria for the commercial experiment

SPEC-011 is successful if it gives us a defensible answer to:

> How should Public Intelligence obtain the awarded-procurement history needed
> to create the first evidence-based commercial profile of ELECTROLEG?

It does **not** need to produce the complete ELECTROLEG profile itself.

A successful result should make the next workflow obvious:

```text
reliable source access
        ↓
supplier award corpus
        ↓
products / classifications
        ↓
buyers
        ↓
competitors
        ↓
white-space opportunities
```

---

## 16. Definition of Done

SPEC-011 is complete when the repository contains enough current evidence to
choose a supplier-award-history acquisition strategy without relying on
arbitrary keyword searches, undocumented assumptions, or chat history.

A future Codex session should be able to read the research and understand:

* what `supplier` means in the available evidence;
* whether targeted access can provide complete supplier coverage;
* whether bulk ingestion is required;
* how supplier identity should be traced;
* what rate-limit uncertainty exists;
* what award history does and does not represent;
* what the next implementation spec must build.

---

## 17. Expected next-spec decision

SPEC-011 should recommend the next implementation spec rather than predetermine
it.

Likely outcomes include:

```text
SPEC-012 — Supplier Award Corpus Ingestion
```

if bulk/hybrid access is selected,

or a smaller targeted supplier-history implementation if current official
evidence establishes a reliable supplier-oriented access mechanism.

Product classifications/items should remain a separate bounded implementation
concern unless SPEC-011 demonstrates that they are inseparable from the
selected ingestion strategy.

---

## 18. Suggested Codex research prompt

```text
/plan

Read:

- AGENTS.md
- docs/vision.md
- docs/specs/README.md
- docs/specs/SPEC-002-sercop-data-source-research.md
- docs/specs/SPEC-003-sercop-targeted-connector.md
- docs/specs/SPEC-005-sercop-historical-bulk-ingestion.md
- docs/specs/SPEC-006-procurement-domain-mapping.md
- docs/specs/SPEC-008-end-to-end-procurement-processing.md
- docs/specs/SPEC-009-basic-procurement-queries.md
- docs/specs/SPEC-010-minimal-intelligence-explorer.md
- docs/research/sercop/
- src/public_intelligence/connectors/sercop/
- src/public_intelligence/domain/procurement/
- src/public_intelligence/persistence/procurement/
- src/public_intelligence/pipelines/
- docs/specs/SPEC-011-sercop-supplier-award-history-access-research.md

Plan SPEC-011 only.

This is a research/discovery spec.

Do not modify production code.

The commercial validation subject is ELECTROLEG S.A., with an initial target
window of 2025-01-01 through 2026-09-18.

Important prior live observations are documented inside SPEC-011.

Treat those observations as evidence to investigate, not universal guarantees.

Return a research plan covering:

1. Official documentation to re-check.
2. Minimal live-request matrix.
3. Positive and negative controls.
4. How supplier-search semantics will be verified against record awards.
5. How exact name, partial name, RUC, and source-ID matching will be evaluated.
6. Whether a complete supplier query is officially supported.
7. Alternative official public-data access mechanisms.
8. Bulk partition discovery.
9. Bulk feasibility for ELECTROLEG 2025-2026.
10. Existing component reuse.
11. Rate-limit evidence collection without stress testing.
12. Award-history versus participation-history semantics.
13. Commercially useful fields already normalized.
14. Important raw fields not yet normalized.
15. Exact research artifacts to create.
16. How Verified / Observed / Unknown will be applied.
17. Decision criteria for TARGETED_API vs BULK vs HYBRID vs INSUFFICIENT_EVIDENCE.
18. Risks and unresolved questions.

Do not implement:

- supplier-award-history ingestion
- automatic backfill
- retries
- scheduler/workers
- entity resolution
- CPC/item normalization
- signals
- opportunities
- scoring
- dashboards
- AI/LLM functionality

Return only the research plan.
```

---

## 19. Human review questions

Before accepting this spec, verify:

* Are we researching the smallest question necessary to unblock ELECTROLEG?
* Does the spec avoid assuming that supplier search is complete?
* Does it clearly distinguish award supplier from participation/proforma provider?
* Does it avoid creating a bulk backfill before proving that bulk is required?
* Does it preserve source-responsibility rules after observing HTTP 429?
* Are live probes kept outside the automated test suite?
* Are strategy-selection rules explicit enough that Codex cannot choose arbitrarily?
* Will the output lead directly to one bounded implementation spec?
* Are product/CPC concerns identified without being pulled prematurely into this research?
