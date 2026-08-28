# SPEC-009 — Basic Procurement Queries

**Status:** Implemented
**Milestone:** 2 — First Usable Product
**Type:** Implementation
**Depends on:** SPEC-001 through SPEC-008

## 1. Context

Public Intelligence can now process one SERCOP bulk partition end-to-end:

```text
SERCOP
  ↓
RawEvidence
  ↓
SercopRecordPackage
  ↓
ProcurementRecord
  ↓
Normalized PostgreSQL
```

After SPEC-008, a developer can populate the normalized procurement tables with one command. However, using normalized data still requires direct SQL knowledge.

SPEC-009 introduces a small, source-independent read/query boundary that answers useful procurement questions without exposing table layout to the rest of the application.

## 2. Goal

Implement a minimal query layer over normalized procurement persistence supporting:

1. list normalized procurements;
2. retrieve one procurement by source + external ID;
3. find procurements by buyer text;
4. find procurements by supplier text;
5. filter by procedure status;
6. filter by procedure value range with honest currency semantics;
7. deterministic pagination/order;
8. enough read data for SPEC-010's explorer.

Conceptual usage:

```python
page = await procurement_queries.search(
    ProcurementSearch(
        buyer="municipio",
        supplier="empresa abc",
        status="complete",
        currency="USD",
        min_value=Decimal("10000"),
        limit=50,
    )
)
```

SPEC-009 remains factual querying only.

## 3. Product value

After SPEC-009 the application should answer questions such as:

```text
¿Qué procesos tengo almacenados?
¿Qué procesos corresponden a este comprador?
¿En qué procesos aparece este proveedor?
¿Qué procesos están completos?
¿Qué procesos tienen un valor mayor a $10,000 en una moneda explícita?
```

Callers should not need to know the normalized table structure or write joins manually.

## 4. Learning walkthrough

### 4.1 Write model vs read model

SPEC-007 focuses on saving/reconstructing a full `ProcurementRecord`.
SPEC-009 focuses on efficiently answering questions.

A full domain object may contain buyer, procedure, suppliers, awards, award suppliers, and contracts. A list/explorer screen may need only source, external ID, buyer name, title, status, value, and updated timestamp.

Small immutable read models are allowed when they remain factual and source-independent.

### 4.2 Query layer is not intelligence

```text
show procurements where buyer contains "Guayaquil"
```

is retrieval.

```text
Guayaquil procurement activity increased 80%
```

is intelligence and belongs later.

### 4.3 Filtering is not entity resolution

Case-insensitive text matching does not mean two differently named organizations are the same entity. Do not reconcile organizations in this spec.

## 5. Architecture

Preferred direction:

```text
future UI/API
      ↓
procurement query boundary
      ↓
normalized PostgreSQL
```

The query layer may depend on persistence/database infrastructure but must not depend on SERCOP DTOs, SERCOP HTTP clients, raw payload parsing, or the SPEC-006 mapper.

Queries operate only on normalized data created by SPEC-007/008.

## 6. Candidate query models

Exact fields must be refined during `/plan`.

```python
@dataclass(frozen=True, slots=True)
class ProcurementSearch:
    buyer: str | None = None
    supplier: str | None = None
    status: str | None = None
    currency: str | None = None
    min_value: Decimal | None = None
    max_value: Decimal | None = None
    limit: int = 50
    offset: int = 0
```

```python
@dataclass(frozen=True, slots=True)
class ProcurementSearchResult:
    source: str
    external_id: str
    buyer_name: str | None
    procedure_title: str | None
    procedure_status: str | None
    procedure_value: Money | None
    updated_at: datetime
```

Avoid generic filter/query DSLs.

## 7. Functional requirements

### FR-1 — Primary search

Provide one small paginated search operation over normalized procurements.

### FR-2 — Source-independent naming

Do not expose source-specific methods such as `search_sercop` or `find_by_ocid`.

### FR-3 — Buyer filter

Support optional buyer-name filtering with case-insensitive literal substring semantics.

- text search only;
- no name normalization;
- no entity inference;
- no raw-evidence reads;
- safe parameterized PostgreSQL.

### FR-4 — Supplier filter

Support optional supplier-name filtering against normalized procurement-level suppliers.

A procurement must appear once even if multiple supplier rows match.

Do not implicitly merge award suppliers into this search surface unless the actual domain contract requires that equivalence.

### FR-5 — Procedure status

Support exact filtering on normalized procedure status. No enums or interpretation.

### FR-6 — Value range and currency

Support inclusive `min_value` and `max_value` using Decimal parameters.

Rules:

- missing values do not match numeric ranges;
- `min_value > max_value` is invalid;
- no currency conversion;
- no inferred currency;
- numeric range filters must use honest currency semantics.

Default preference: require an explicit `currency` whenever `min_value` or `max_value` is provided, unless `/plan` demonstrates another unambiguous design.

### FR-7 — Deterministic ordering

Default preference:

```text
updated_at DESC,
source ASC,
external_id ASC
```

Do not expose arbitrary sorting yet.

### FR-8 — Pagination

Use bounded offset/limit pagination:

- default 50;
- max 200;
- limit > 0;
- offset >= 0.

No cursor pagination yet.

### FR-9 — Result page/count

`/plan` must decide whether search returns only items or a small page model with total count. Preferred if simple:

```python
ProcurementSearchPage(
    items=...,
    total=...,
    limit=...,
    offset=...,
)
```

### FR-10 — Full detail lookup

Reuse `ProcurementRepository.get()` for one full procurement by source + external ID. Do not duplicate aggregate reconstruction.

### FR-11 — Overview statistics

A very small factual overview may be proposed only if it remains unambiguous and directly helps SPEC-010. Do not implement trends, rankings, or historical comparisons here.

### FR-12 — No raw reads

General search must never decode `raw_evidence`.

### FR-13 — Existing SQL stack

Use Psycopg/PostgreSQL and explicit parameterized SQL. No ORM.

### FR-14 — LIKE safety

All user-provided values must be query parameters. Literal substring search must explicitly handle `%`, `_`, and the chosen escape character.

### FR-15 — Blank filters

Blank/whitespace-only buyer or supplier filters should be rejected rather than interpreted as match-all.

## 8. Read-model design

Search-result models should be immutable and minimal. Do not return database row dictionaries directly.

Possible result fields:

- source;
- external_id;
- buyer_name;
- procedure_title;
- procedure_status;
- procedure method/category only if immediately useful;
- procedure Money;
- supplier summary only if cheap and unambiguous;
- updated_at.

Resist adding fields just because they exist in the tables.

## 9. SQL/query semantics for `/plan`

The implementation plan must explicitly define:

1. buyer substring behavior;
2. supplier matching/deduplication;
3. LIKE/ILIKE wildcard escaping;
4. value + currency semantics;
5. deterministic ordering;
6. pagination validation;
7. total-count semantics;
8. whether supplier summary appears in list rows;
9. whether overview statistics belong here;
10. whether any indexes are justified now.

Default: no speculative indexes.

## 10. Boundary placement

Candidate locations:

```text
src/public_intelligence/persistence/procurement/queries.py
```

or a small application read boundary.

The `/plan` must choose the smallest consistent design.

Important distinction:

- `ProcurementRepository`: aggregate save/get;
- query boundary: search/read projections.

Do not turn `ProcurementRepository` into a large generic finder repository.

## 11. Testing strategy

- Real disposable PostgreSQL.
- Prefer seeding via `ProcurementRepository.save()`.
- No live SERCOP.
- Search-all deterministic pagination.
- Buyer case-insensitive/literal substring tests including `%` and `_`.
- Supplier matching and no duplicate procurement rows.
- Exact status filtering.
- Decimal min/max boundaries.
- Missing money excluded from ranges.
- Currency behavior/missing currency.
- Combined filters use AND.
- Ordering deterministic.
- Pagination boundaries.
- Total count if implemented.
- Source independence with `sercop` and `example_source`.
- Full-detail get reuses existing repository semantics.
- Existing SPEC-001 through SPEC-008 suite remains green.

## 12. Non-goals

Do not implement:

- HTTP API;
- UI/dashboard/charts;
- rankings/trends;
- intelligence signals;
- entity resolution/fuzzy organization matching;
- Elasticsearch/OpenSearch/full-text infrastructure;
- vector search;
- LLM/natural-language-to-SQL;
- saved searches;
- exports;
- background jobs;
- generic reporting framework.

## 13. Acceptance criteria

### Architecture
- [x] Query boundary reads only normalized procurement persistence.
- [x] Query boundary is source-independent.
- [x] SERCOP connector/DTO code is not imported.
- [x] Raw evidence is not decoded for search.
- [x] Existing Psycopg/PostgreSQL infrastructure is reused.
- [x] No ORM/generic query framework is added.

### Search
- [x] Paginated procurement search exists.
- [x] Buyer-name filtering works.
- [x] Supplier-name filtering works.
- [x] Procedure-status filtering works.
- [x] Procedure-value filtering uses honest currency semantics.
- [x] Combined filters use AND semantics.
- [x] Deterministic ordering is defined.
- [x] Child joins do not duplicate procurements.
- [x] Blank text filters are explicit.
- [x] LIKE wildcard behavior is safe/tested.

### Read models
- [x] Immutable minimal result model exists.
- [x] Pagination metadata is explicit.
- [x] Search input validates limit/offset/range rules.
- [x] Decimal is preserved.
- [x] Missing money differs from zero.
- [x] No source-specific identity names leak into read models.

### Detail
- [x] Full procurement lookup by source + external_id is available.
- [x] Existing ProcurementRepository reconstruction is reused.
- [x] Unknown identity returns None.

### Tests
- [x] Real disposable PostgreSQL is used.
- [x] Buyer search is tested.
- [x] Supplier search/dedup is tested.
- [x] Status filtering is tested.
- [x] Value/currency behavior is tested.
- [x] Combined filters are tested.
- [x] Ordering is tested.
- [x] Pagination boundaries are tested.
- [x] Source independence is tested.
- [x] Existing SPEC-001 through SPEC-008 tests pass.
- [x] No live SERCOP calls occur.

### Scope
- [x] No API/UI.
- [x] No analytics/signals/trends.
- [x] No entity resolution/fuzzy matching.
- [x] No search engine.
- [x] No natural-language querying.
- [x] No generic reporting framework.
- [x] No scheduler/background worker.

### Quality
- [x] No unnecessary dependency.
- [x] Lockfile remains consistent.
- [x] Ruff format/lint pass.
- [x] mypy passes.
- [x] pytest passes.
- [x] migration validation remains green.
- [x] git diff --check passes.

## 14. Definition of Done

SPEC-009 is complete when application code can ask useful factual procurement questions through a stable source-independent query boundary without writing SQL or understanding normalized table joins.

Example:

```python
page = await queries.search(
    ProcurementSearch(
        buyer="Guayaquil",
        status="complete",
        currency="USD",
        min_value=Decimal("10000"),
    )
)
```

This boundary becomes the main data source for SPEC-010's Minimal Intelligence Explorer.

## 15. Roadmap

```text
SPEC-009 — Basic Procurement Queries
        ↓
SPEC-010 — Minimal Intelligence Explorer
        ↓
SPEC-011 — First Deterministic Signal
```

## 16. Suggested `/plan` prompt

```text
/plan

Read:
- AGENTS.md
- docs/vision.md
- docs/adr/ADR-001-modular-monolith.md
- docs/adr/ADR-002-postgresql-raw-evidence-persistence.md
- docs/specs/SPEC-006-procurement-domain-mapping.md
- docs/specs/SPEC-007-normalized-procurement-persistence.md
- docs/specs/SPEC-008-end-to-end-procurement-processing.md
- src/public_intelligence/domain/procurement/
- src/public_intelligence/persistence/
- tests/persistence/
- docs/specs/SPEC-009-basic-procurement-queries.md

Plan SPEC-009. Do not modify files.

Explicitly address:
1. Exact query boundary location and public interface.
2. ProcurementSearch fields and validation.
3. ProcurementSearchResult exact fields.
4. Whether ProcurementSearchPage includes total count.
5. Buyer substring semantics.
6. Supplier search source and deduplication.
7. LIKE/ILIKE wildcard escaping.
8. Status filtering.
9. Decimal value filtering.
10. Exact currency semantics for min/max value filters.
11. Deterministic ordering.
12. Limit/offset rules.
13. Whether supplier summaries belong in list results.
14. Whether minimal overview statistics belong in SPEC-009 or should be deferred.
15. Full-detail get delegation to ProcurementRepository.
16. SQL shape and parameterization.
17. Whether any indexes are justified now.
18. Integration-test data setup.
19. Exact tests.
20. Exact files to create/modify.
21. Whether any migration, dependency, or ADR is needed.
22. Overengineering risks.

Do not implement:
- API/UI
- dashboard/charts
- historical analytics
- rankings
- signals/events/opportunities
- entity resolution/fuzzy matching
- full-text/search engine
- natural-language querying
- generic reporting/query framework
- background jobs

Return only the implementation plan.
```
