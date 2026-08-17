# SPEC-002 — SERCOP Data Source Research

**Status:** Implemented
**Milestone:** 1 — First Real Intelligence  
**Type:** Research / Discovery  
**Date drafted:** 2026-08-14

## Context

Public Intelligence needs its first real public-data source.

SERCOP is the initial candidate because Ecuador's public procurement open-data platform exposes contracting information using the Open Contracting Data Standard (OCDS) and provides both query-oriented API access and bulk downloads.

Before implementing a production connector, ingestion pipeline, persistence model, or procurement domain model, the project needs evidence about:

- how SERCOP data can be accessed
- which access mode is appropriate for historical ingestion versus targeted lookups
- what the real response structures look like
- which OCDS concepts SERCOP actually publishes
- what identifiers can be relied upon
- what data-quality limitations exist
- what historical information can be reconstructed
- which source-specific concepts must remain isolated from the future domain

This spec is intentionally research-first.

The output of SPEC-002 is knowledge and representative source samples, not production integration code.

---

## Problem

Designing a SERCOP connector directly from generic OCDS documentation would risk building against assumptions rather than the actual Ecuadorian publication.

Likewise, designing the Public Intelligence procurement domain directly from SERCOP payloads would risk leaking source-specific representations into the core domain.

We need to understand the source before designing either boundary.

---

## Goal

Produce a documented, evidence-based profile of SERCOP as a Public Intelligence source.

At the end of this spec, the repository should make it possible to answer:

1. What official SERCOP open-data access mechanisms are available?
2. What is each mechanism best suited for?
3. What date/history coverage is available?
4. What identifiers are present and how stable do they appear?
5. What does a real search result contain?
6. What does a real OCDS record contain?
7. Which procurement lifecycle sections are actually populated?
8. How are buyers and suppliers represented?
9. How are values, currencies, dates, statuses, classifications, items, awards, and contracts represented?
10. Does the SERCOP publication expose enough history to derive internal events?
11. What data-quality or consistency issues are observable?
12. What ingestion strategy should SPEC-003 investigate or implement?
13. Which unanswered questions remain before production ingestion?

---

## Non-goals

SPEC-002 does **not** implement:

- a production SERCOP connector
- scheduled ingestion
- PostgreSQL
- database schemas
- repositories
- ORM models
- domain entities for procurement
- internal business events
- business signals
- opportunity scoring
- entity resolution
- an API endpoint for procurement
- frontend functionality
- AI/LLM functionality
- background workers
- Docker
- cloud infrastructure
- scraping of authenticated SERCOP systems
- CAPTCHA bypass
- automated access to non-public/private endpoints
- broad crawling of SERCOP
- performance optimization for large-scale downloads

Do not add runtime or development dependencies solely for this research.

---

## Known official starting points

These facts are starting hypotheses verified from official public documentation at the time this spec was drafted. They must still be validated during execution because public services can change.

### Public OCDS platform

SERCOP publishes a Contrataciones Abiertas Ecuador platform using OCDS.

### Search API

Official documentation describes a search endpoint:

```text
https://datosabiertos.compraspublicas.gob.ec/PLATAFORMA/api/search_ocds
```

Documented parameters include:

- `year` — required
- `search` — required, minimum three characters
- `page` — optional
- `buyer` — optional
- `supplier` — optional

The documented year range begins in 2015 and extends through the current year.

### Record API

Official documentation describes record lookup by OCID:

```text
https://datosabiertos.compraspublicas.gob.ec/PLATAFORMA/api/record
```

with:

```text
ocid=<contracting-process-identifier>
```

### Bulk access

The official platform also exposes bulk procurement downloads filtered by:

- year
- month
- procurement type

with formats including:

- JSON
- CSV
- XLSX

### Usage

The official platform states that its published open procurement data is freely accessible and does not impose usage restrictions.

This applies to the open-data publication itself and does not authorize bypassing restrictions on other SERCOP systems.

---

## OCDS concepts to investigate

Generic OCDS documentation must be used only as a reference for understanding the source. Actual SERCOP samples are authoritative for this project.

Investigate whether and how SERCOP populates:

```text
ocid
id
date
tag
initiationType
parties
buyer
planning
tender
awards
contracts
relatedProcesses
language
```

For parties, investigate at minimum:

```text
parties[].id
parties[].name
parties[].identifier
parties[].roles
```

For tenders:

```text
tender.id
tender.title
tender.description
tender.status
tender.procurementMethod
tender.procurementMethodDetails
tender.mainProcurementCategory
tender.value
tender.items
tender.tenderPeriod
tender.enquiryPeriod
tender.awardPeriod
tender.contractPeriod
tender.procuringEntity
```

For awards:

```text
awards[].id
awards[].title
awards[].status
awards[].date
awards[].value
awards[].suppliers
awards[].items
```

For contracts:

```text
contracts[].id
contracts[].awardID
contracts[].status
contracts[].dateSigned
contracts[].value
contracts[].period
contracts[].items
contracts[].implementation
```

This list is exploratory, not a proposed internal domain model.

Do not create internal models merely because these OCDS fields exist.

---

## Research questions

### RQ-1 — Access mechanisms

Document every official open-data mechanism discovered.

For each mechanism record:

- purpose
- URL/endpoint or navigation path
- authentication requirement
- query parameters
- pagination
- response format
- apparent limits
- historical coverage
- suitability for targeted lookup
- suitability for bulk historical ingestion

At minimum compare:

1. keyword search API
2. OCID record API
3. bulk downloads

### RQ-2 — API authentication and restrictions

Determine whether the public open-data API:

- requires authentication
- requires an API key
- exposes documented rate limits
- exposes pagination limits
- returns useful HTTP error information

Do not stress-test the service.

Use only a small number of requests necessary to understand normal behavior.

If a restriction cannot be established from official evidence, record it as `Unknown`; do not infer that no restriction exists.

### RQ-3 — Historical coverage

Verify the earliest and latest years practically exposed by the official source.

Distinguish between:

- documented coverage
- coverage observed from successful sample access

Do not download the entire historical dataset in SPEC-002.

### RQ-4 — Search response

Capture and describe at least one successful response from the official keyword-search endpoint.

Document fields actually returned by search.

Determine whether search results are:

- full OCDS records
- summaries/index entries
- another SERCOP-specific representation

Identify the field used to transition from a search result to a full record lookup.

### RQ-5 — Record structure

For representative OCIDs, inspect the official record response.

Document:

- top-level structure
- package metadata
- `ocid`
- `releases`
- `compiledRelease`
- `versionedRelease`, if present
- extensions, if declared
- source-specific additional fields, if present

Do not assume all standard OCDS fields are populated.

### RQ-6 — Lifecycle/history semantics

Determine whether SERCOP data allows us to observe procurement changes over time.

Investigate:

- number of releases per sampled OCID
- release dates
- release tags
- whether previous states are retained
- whether a `compiledRelease` is available
- whether a `versionedRelease` is available
- whether lifecycle transitions can be inferred reliably

Explicitly distinguish:

```text
OCDS release
```

from the future Public Intelligence concept:

```text
Event
```

Do not define Public Intelligence event mappings in this spec.

### RQ-7 — Organization identifiers

Investigate buyer and supplier identity representation.

Document examples of:

- OCDS party ID
- identifier scheme
- identifier value
- organization name
- roles
- RUC representation, if present

Answer:

- Can RUC be extracted reliably?
- Is the buyer also represented in `parties`?
- Are award suppliers represented in `parties`?
- Can the same organization appear with inconsistent IDs or names in the inspected samples?

Do not implement entity resolution.

### RQ-8 — Procurement identifiers

Document the apparent roles of:

- `ocid`
- OCDS release `id`
- tender/process identifiers
- award IDs
- contract IDs
- any SERCOP-specific identifier encountered

Recommend which identifier should be treated as the external source identifier for a contracting process in a future connector.

This is a recommendation, not yet a domain commitment.

### RQ-9 — Money

Inspect representation of:

- tender value
- award value
- contract value
- amount
- currency
- null/missing values

Record whether USD appears consistently in the inspected samples.

Do not assume currency when it is absent.

### RQ-10 — Dates

Inventory relevant dates actually present in representative records.

Examples may include:

- release date
- publication-related dates
- tender period
- award date
- contract signing date
- contract period

Document:

- date/time format
- timezone/offset presence
- nullability
- observed inconsistencies

Do not normalize dates in production code.

### RQ-11 — Procurement classifications and items

Investigate:

- item descriptions
- quantities
- units
- classification scheme
- classification IDs/codes
- procurement category
- procurement method/type

Determine whether product/service classification could later support opportunity matching.

Do not build classification logic yet.

### RQ-12 — Status semantics

Inventory observed statuses for:

- tender
- award
- contract

Compare SERCOP values to the applicable OCDS codelists where relevant.

Document extensions or non-standard values if encountered.

### RQ-13 — Documents and source links

Investigate whether records expose:

- tender documents
- award documents
- contract documents
- source URLs
- document download URLs

Do not bulk-download documents.

Record only representative metadata/links if present.

### RQ-14 — Bulk-download shape

Inspect a small representative bulk-download artifact if practical without downloading an unnecessarily large file.

Determine:

- whether JSON contains release packages, records, flattened rows, or another structure
- whether CSV/XLSX flatten nested OCDS information
- approximate organization of files
- whether bulk JSON is better suited for lossless historical ingestion than tabular formats

Do not ingest the full historical dataset.

### RQ-15 — Data quality

Record only issues supported by inspected evidence.

Look for examples such as:

- missing identifiers
- missing supplier information
- duplicate-looking records
- inconsistent organization names
- null monetary values
- fields present in some procurement types but not others
- unexpected data types
- encoding issues
- incomplete lifecycle sections

Do not generalize from one sample to the entire dataset.

Classify findings as:

- Observed
- Suspected
- Unknown

### RQ-16 — Access-strategy recommendation

Conclude with a recommendation for future implementation.

At minimum answer:

1. Which mechanism should SPEC-003 use for targeted connector operations?
2. Which mechanism should a later historical-ingestion spec use?
3. Should raw JSON be preserved?
4. Which source identifiers must be retained?
5. What minimum provenance metadata should be stored?
6. What uncertainty must remain source-specific?

The recommendation should optimize for:

- correctness
- reproducibility
- source fidelity
- simplicity
- extensibility

not maximum throughput.

---

## Representative sampling strategy

Use a deliberately small sample.

Target at least **three successfully retrievable contracting processes**, preferably including:

1. one process from the current year
2. one process from an older year
3. processes representing at least two procurement types if practical

If easy to obtain, prefer samples that exercise different lifecycle states or populated sections.

Do not choose samples solely because they contain every possible field.

Realistic variation is useful.

### Sample provenance

For every saved source sample, document:

- retrieval date
- official endpoint/mechanism
- request parameters or OCID
- HTTP status
- content type
- whether the sample is complete or truncated
- any manual modifications

Raw samples should not be manually "cleaned."

If a sample contains data that should not be committed for a concrete legal/privacy reason, document the issue instead of silently altering it.

---

## Expected research artifacts

Create:

```text
docs/research/sercop/
├── README.md
├── access.md
├── data-model.md
├── data-quality.md
├── ingestion-recommendation.md
└── samples/
    ├── README.md
    └── <representative raw samples>
```

### `README.md`

Executive research summary containing:

- source overview
- research date
- key findings
- key uncertainties
- conclusion
- links to the detailed research files

### `access.md`

Document:

- API mechanisms
- parameters
- authentication
- pagination
- observed behavior
- historical coverage
- bulk-download mechanisms
- access limitations/unknowns

### `data-model.md`

Document the observed SERCOP/OCDS structure.

Include a concise diagram such as:

```text
Contracting Process (ocid)
        |
        +-- releases[]
        |
        +-- compiledRelease?
               |
               +-- parties[]
               +-- buyer
               +-- tender
               +-- awards[]
               `-- contracts[]
```

The diagram must reflect observed data, not assumptions.

### `data-quality.md`

Document:

- observed issues
- suspected issues
- unknowns
- sample-specific caveats
- implications for a future connector

### `ingestion-recommendation.md`

Provide the decision-oriented output of the research.

Recommend:

- targeted lookup strategy
- future historical ingestion strategy
- raw-data preservation strategy
- likely connector responsibilities
- likely provenance fields
- unresolved risks
- recommended scope of SPEC-003

Do **not** implement SPEC-003.

### `samples/`

Store only a small number of raw representative responses/artifacts needed to support the findings.

Avoid large files.

---

## Research methodology

### Step 1 — Read project context

Read:

- `AGENTS.md`
- `docs/vision.md`
- `docs/adr/ADR-001-modular-monolith.md`
- `docs/specs/README.md`
- this spec

### Step 2 — Read official source documentation

Use official SERCOP open-data documentation as the primary source for SERCOP-specific behavior.

Use official Open Contracting Data Standard documentation as the primary reference for generic OCDS semantics.

Do not use third-party blog posts as authoritative evidence for the source contract.

### Step 3 — Inspect real source responses

Use a small number of read-only requests to public endpoints.

Do not:

- crawl aggressively
- bypass technical controls
- access authenticated areas
- perform load testing

### Step 4 — Save representative evidence

Preserve small raw samples where appropriate.

Do not normalize or transform them into our domain.

### Step 5 — Compare source behavior with OCDS

Identify:

- standard OCDS structures
- optional structures
- SERCOP-specific extensions/choices
- absent fields that matter to our goals

### Step 6 — Produce implementation recommendation

Recommend the smallest sensible scope for the next implementation spec.

---

## Technical constraints

- Follow `AGENTS.md`.
- Follow ADR-001.
- Do not modify production application behavior.
- Do not add runtime dependencies.
- Do not add development dependencies unless explicitly approved.
- Prefer existing standard-library capabilities and command-line tools for small research requests.
- Do not introduce a reusable connector abstraction.
- Do not create domain classes.
- Do not create persistence code.
- Do not create generic ingestion frameworks.
- Do not add environment/settings machinery.
- Do not implement retries, caching, or concurrency as production utilities.
- Keep research-only artifacts clearly separated from `src/`.
- Do not infer undocumented guarantees from a small sample.
- Distinguish verified facts from hypotheses.

---

## Source ethics and operational safety

The research must use only publicly accessible open-data functionality.

Respect:

- published access rules
- normal request rates
- public-data boundaries
- source availability

If an endpoint rejects or throttles requests:

1. stop repeated attempts
2. record the observed behavior
3. do not attempt to circumvent it

Do not access or automate the authenticated SOCE application as part of SPEC-002.

---

## Acceptance criteria

### Documentation

- [x] `docs/research/sercop/README.md` exists.
- [x] `access.md` documents all official open-data mechanisms investigated.
- [x] `data-model.md` documents structures observed from real SERCOP data.
- [x] `data-quality.md` separates Observed, Suspected, and Unknown findings.
- [x] `ingestion-recommendation.md` recommends a next-step implementation strategy.

### Source access

- [x] The documented SERCOP keyword-search endpoint has been investigated.
- [x] The documented SERCOP record-by-OCID endpoint has been investigated.
- [x] Bulk-download availability and formats have been investigated.
- [x] Authentication/API-key requirements are documented as Verified or Unknown.
- [x] Pagination behavior is documented as Verified or Unknown.
- [x] Rate-limit information is documented as Verified or Unknown rather than guessed.

### Samples

- [x] At least three representative contracting processes have been inspected when official endpoint availability permits.
- [x] At least one sample is from the current year when official data permits.
- [x] At least one sample is from an older year when official data permits.
- [x] At least two procurement types are represented when practical.
- [x] Saved samples include provenance metadata.
- [x] Saved raw samples have not been semantically cleaned or normalized.
- [x] No unnecessarily large dataset is committed.

### Data semantics

- [x] The role of `ocid` is documented.
- [x] Search-result identifiers are documented.
- [x] Release/record/compiled-release behavior observed from SERCOP is documented.
- [x] Buyer representation is documented.
- [x] Supplier representation is documented.
- [x] Procurement identifiers are documented.
- [x] Monetary representation is documented.
- [x] Relevant dates are documented.
- [x] Tender, award, and contract structures are documented where present.
- [x] Classification/item information is documented where present.
- [x] Status values are documented where present.
- [x] Source/document links are documented where present.

### Historical/event feasibility

- [x] The research states whether multiple releases per OCID were observed.
- [x] The research states whether a compiled release was observed.
- [x] The research states whether a versioned release was observed.
- [x] The research evaluates whether historical lifecycle changes appear derivable.
- [x] No Public Intelligence event mapping is implemented.

### Architecture and scope

- [x] No SERCOP production connector is implemented.
- [x] No production application behavior changes.
- [x] No database dependency is introduced.
- [x] No domain model is introduced.
- [x] No new speculative abstraction is introduced.
- [x] Existing SPEC-001 quality checks still pass after documentation/sample changes.

### Recommendation

- [x] A preferred mechanism for targeted lookups is recommended.
- [x] A preferred mechanism for future historical ingestion is recommended.
- [x] Raw-data preservation recommendations are documented.
- [x] Required provenance/source identifiers are recommended.
- [x] Remaining unknowns are explicitly listed.
- [x] A bounded proposal for SPEC-003 is provided, without implementing it.

---

## Failure / limited-access behavior

Public services can be unavailable.

If SERCOP endpoints cannot be reached from the Codex environment:

- do not fabricate samples
- do not weaken acceptance criteria silently
- document the failure and evidence
- use official documentation for what can be established
- mark runtime observations as `Unknown`
- report which acceptance criteria remain blocked

A temporarily unavailable external service is a research result, not a reason to invent behavior.

---

## Definition of Done

SPEC-002 is complete when the repository contains enough evidence to design the first SERCOP implementation spec without relying on generic OCDS assumptions or chat history.

A future developer or Codex session should be able to read the research artifacts and understand:

- how SERCOP can be accessed
- what the source actually returns
- which parts of OCDS matter
- what is uncertain
- what the first production connector should and should not do

---

## Suggested Codex planning prompt

Before modifying files:

```text
Read AGENTS.md, the project vision, ADR-001, the specs README,
and SPEC-002.

Do not implement a production connector.

Inspect the repository and the official SERCOP/OCDS sources described
by SPEC-002.

First provide a research plan containing:

1. Official sources you will inspect.
2. Public endpoints/mechanisms you will test.
3. Minimal sampling strategy.
4. Research artifacts you will create.
5. How you will preserve sample provenance.
6. How you will distinguish verified facts from assumptions.
7. Risks or ambiguities in SPEC-002.

Do not modify repository files yet.
```

---

## Open questions

### OQ-1 — API versus bulk ingestion

The search/record API appears suitable for targeted access, while bulk downloads may be more appropriate for historical ingestion.

SPEC-002 must validate this rather than treating it as decided.

### OQ-2 — Raw-storage unit

It is not yet decided whether a future raw layer should preserve:

- individual API records
- individual releases
- downloaded bulk artifacts
- some combination of these

SPEC-002 should collect evidence, not make an irreversible persistence design.

### OQ-3 — Event derivation

OCDS represents changes through releases and records.

It is not yet known whether SERCOP's publication has sufficient granularity and consistency for the Public Intelligence event model we envision.

Do not define event mappings until real examples have been inspected.

### OQ-4 — Entity identity

RUC may be useful for Ecuadorian organization resolution, but the reliability and consistency of its representation must be verified from source samples.

Do not design entity resolution in this spec.

### OQ-5 — First production connector scope

SPEC-003 should be defined from the research results.

It may be smaller than a complete OCDS connector.

Prefer implementing only the source capabilities needed by the first product milestone.
