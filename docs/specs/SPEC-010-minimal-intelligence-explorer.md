# SPEC-010 — Minimal Intelligence Explorer

**Status:** Implemented  
**Milestone:** 2 — First Usable Product  
**Type:** Implementation  
**Depends on:** SPEC-001 through SPEC-009

## 1. Context

Public Intelligence can now process SERCOP data end-to-end, persist normalized procurement data, and query that data through a source-independent read boundary.

Current flow:

```text
SERCOP
  ↓
RawEvidence
  ↓
ProcurementRecord
  ↓
Normalized PostgreSQL
  ↓
ProcurementQueries
```

What is still missing is a browser-accessible surface where a person can explore that information without writing SQL or Python.

SPEC-010 introduces the first minimal explorer.

## 2. Problem

Today, useful data exists but is only accessible through code, SQL, tests, or CLI commands.

A user cannot yet:

- list procurements;
- search by buyer;
- search by supplier;
- filter by status;
- filter by currency/value;
- paginate results;
- open one procurement;
- inspect buyer, procedure, suppliers, awards, award suppliers, and contracts.

## 3. Goal

Create a minimal local web explorer over normalized procurement data using the existing FastAPI application and SPEC-009 query boundary.

Conceptual flow:

```text
Browser
   ↓
FastAPI presentation layer
   ↓
ProcurementQueries
   ↓
Normalized PostgreSQL
```

No raw payload parsing is required for ordinary exploration.

## 4. Product value

After SPEC-010, Public Intelligence should be demonstrable as a small usable product.

A user should be able to open the application locally and see a search/filter screen, a paginated result list, and a factual procurement detail view.

This is the first complete visual vertical slice.

## 5. Architectural principles

- Reuse the existing FastAPI app factory.
- Presentation must use ProcurementQueries / existing detail boundary.
- No direct procurement SQL in web handlers.
- No SERCOP DTO or mapper imports in presentation.
- No raw evidence decoding.
- Reuse one application-managed PostgreSQL pool.
- Do not create a second web server.
- Do not introduce a generic presentation framework.

## 6. Functional requirements

### FR-1 — Explorer home

Provide a browser-accessible explorer page at `/` or an equally simple route.

It should include:

- product heading;
- procurement filters;
- total result count;
- paginated result list;
- clear empty state.

### FR-2 — Search filters

Expose exactly the approved SPEC-009 filters:

- buyer;
- supplier;
- status;
- currency;
- min_value;
- max_value;
- limit;
- offset.

Do not invent different semantics in the UI layer.

### FR-3 — Search projection

List results should expose only:

- source;
- external_id;
- buyer_name;
- procedure_title;
- procedure_status;
- procedure_value;
- updated_at.

Do not expose internal procurement UUIDs.

### FR-4 — Pagination

Display:

- total matches;
- current result range;
- previous/next navigation.

Use SPEC-009 `total`, `limit`, and `offset`.

No infinite scroll.

### FR-5 — Money display

Preserve Decimal semantics.

- missing money != zero;
- show currency when present;
- do not infer currency;
- do not convert currencies;
- do not pass Decimal through float.

### FR-6 — Detail

Provide a route/page to open one procurement by source + external ID.

Display factual sections:

- identity;
- buyer;
- procedure;
- procurement-level suppliers;
- awards;
- award suppliers;
- contracts;
- evidence UUID when present.

Unknown procurement must return an explicit not-found result.

### FR-7 — Missing vs empty

Where the domain preserves the distinction, render useful labels for:

- unknown/not supplied;
- known collection with zero items.

Keep wording simple.

### FR-8 — Source independence

Use labels such as:

- Source
- External ID
- Buyer

Do not hard-code OCID or SERCOP-specific field names in the presentation model.

### FR-9 — HTML approach

Prefer the smallest implementation:

```text
server-rendered HTML
+
small CSS
```

The `/plan` must inspect the repo and decide between:

- plain HTML response construction;
- Jinja2 if already installed or strongly justified;
- static HTML + minimal JS consuming JSON endpoints.

Do not introduce React/Vue/Svelte, npm, or frontend build tooling.

### FR-10 — Optional JSON endpoints

If JSON endpoints materially simplify the explorer, keep them small and explicit.

Conceptual endpoints:

```text
GET /api/procurements
GET /api/procurements/{source}/{external_id}
```

Response serialization must handle Decimal and datetime explicitly.

Money amount should preferably serialize as a string.

### FR-11 — Validation

Invalid query parameters must produce clear client errors.

Examples:

- whitespace-only filters;
- invalid Decimal;
- min/max without currency;
- min > max;
- invalid limit/offset.

Do not silently convert validation failures into empty results.

### FR-12 — Configuration/lifecycle

Use existing DATABASE_URL/config behavior.

Create/reuse the database pool through FastAPI lifespan.

Do not create a pool per request.

Do not run migrations automatically.

### FR-13 — Health regression

`GET /health` must remain exactly:

```json
{"status":"ok"}
```

## 7. Suggested UI structure

```text
/
├── heading
├── filters
├── result count
├── results
└── pagination

/procurements/<identity>
├── identity
├── buyer
├── procedure
├── suppliers
├── awards
└── contracts
```

Favor simple server-rendered navigation over SPA behavior.

## 8. Empty states

Examples:

```text
No procurements match these filters.
```

For an empty normalized database:

```text
No normalized procurements are available yet.
Run the procurement processing pipeline first.
```

The UI must not trigger ingestion automatically.

## 9. Testing strategy

- Reuse existing FastAPI test approach.
- Use real disposable PostgreSQL where query behavior matters.
- No live SERCOP calls.
- Test `/health` regression.
- Test default listing.
- Test buyer/supplier/status/currency/value filters.
- Test pagination and total count.
- Test invalid query behavior.
- Test Decimal precision, zero, missing money, nullable currency.
- Test known procurement detail.
- Test unknown procurement.
- Test suppliers, awards, award suppliers, contracts, evidence reference.
- Test a synthetic non-SERCOP source.
- Verify no raw evidence decoding is required.
- Verify application lifecycle closes resources.
- Existing SPEC-001 through SPEC-009 suite remains green.

## 10. Non-goals

Do not implement:

- ingestion buttons;
- scheduler/workers;
- authentication/users/roles;
- multi-tenant authorization;
- charts;
- dashboards;
- rankings;
- trends;
- historical comparisons;
- signals;
- opportunities;
- alerts;
- entity resolution;
- organization/supplier profiles;
- exports/CSV;
- raw evidence viewer;
- natural-language search;
- LLM integration;
- frontend framework/build system;
- search engine;
- WebSockets/live updates.

## 11. Acceptance criteria

### Architecture

- [x] Existing FastAPI app is reused.
- [x] Presentation depends on ProcurementQueries/detail boundary.
- [x] Web handlers contain no direct procurement SQL.
- [x] No SERCOP DTO/mapper dependency exists in presentation.
- [x] No raw evidence decoding is required.
- [x] One application-managed DB pool is reused.

### Explorer

- [x] Browser-accessible procurement explorer exists.
- [x] Default procurement list renders.
- [x] Buyer filter is usable.
- [x] Supplier filter is usable.
- [x] Status filter is usable.
- [x] Currency/value filters are usable.
- [x] Total matches are visible.
- [x] Pagination is usable.
- [x] Empty-state messaging exists.

### Results

- [x] List shows source-independent identity.
- [x] Buyer/title/status/value are displayed.
- [x] Missing money differs visually from zero.
- [x] Currency is not inferred.
- [x] Internal UUID is not exposed in list.
- [x] Result order follows SPEC-009.

### Detail

- [x] One procurement can be opened.
- [x] Unknown procurement gives not-found.
- [x] Buyer is displayed.
- [x] Procedure is displayed.
- [x] Procurement suppliers are displayed.
- [x] Awards are displayed.
- [x] Award suppliers remain associated with awards.
- [x] Contracts are displayed.
- [x] Evidence UUID is displayed when present.
- [x] No raw payload is exposed.

### HTTP / validation

- [x] Search HTTP boundary uses SPEC-009 validation semantics.
- [x] Decimal serialization/display never passes through float.
- [x] Datetime serialization is deterministic.
- [x] Invalid filters produce explicit client errors.
- [x] `/health` remains exactly compatible.

### Tests

- [x] FastAPI web integration is tested.
- [x] Real PostgreSQL is used for query-integrated tests.
- [x] Default listing/filter/pagination tests exist.
- [x] Invalid query tests exist.
- [x] Money tests exist.
- [x] Detail tests exist.
- [x] Not-found test exists.
- [x] Synthetic second source renders correctly.
- [x] No live SERCOP calls occur.
- [x] Existing SPEC-001 through SPEC-009 tests pass.

### Scope

- [x] No ingestion UI.
- [x] No charts/dashboard analytics.
- [x] No signals/opportunities.
- [x] No entity resolution.
- [x] No authentication.
- [x] No exports.
- [x] No raw evidence viewer.
- [x] No frontend framework/build system.
- [x] No natural-language/LLM search.

### Quality

- [x] No unnecessary dependencies.
- [x] lockfile consistent.
- [x] Ruff format/lint pass.
- [x] mypy passes.
- [x] pytest passes.
- [x] migration validation passes.
- [x] git diff --check passes.

## 12. Definition of Done

SPEC-010 is complete when a developer can:

```text
1. run the procurement pipeline
2. start the existing FastAPI application
3. open a browser
4. search/filter normalized procurements
5. open one procurement
6. inspect buyer/procedure/suppliers/awards/contracts
```

without writing SQL or Python.

## 13. Product milestone checkpoint

At completion:

```text
SPEC-008 → data enters product
SPEC-009 → product can query data
SPEC-010 → human can explore data
```

Next:

```text
SPEC-011 — First Deterministic Signal
```

## 14. Suggested `/plan` prompt

```text
/plan

Read:

- AGENTS.md
- docs/vision.md
- docs/adr/ADR-001-modular-monolith.md
- docs/adr/ADR-002-postgresql-raw-evidence-persistence.md
- docs/specs/SPEC-008-end-to-end-procurement-processing.md
- docs/specs/SPEC-009-basic-procurement-queries.md
- src/public_intelligence/api/
- src/public_intelligence/persistence/procurement/
- src/public_intelligence/domain/procurement/
- tests/
- docs/specs/SPEC-010-minimal-intelligence-explorer.md

Plan SPEC-010. Do not modify files.

Explicitly address:

1. Current FastAPI app factory/lifespan and exact integration point.
2. Exact browser routes.
3. Whether JSON API endpoints are needed or server-rendered HTML alone is simpler.
4. Exact HTML/template technology and whether any dependency is required.
5. ProcurementQueries construction/reuse through application lifespan.
6. Search query-parameter parsing into ProcurementSearch.
7. HTTP validation/error mapping.
8. Exact list result fields and presentation.
9. Money Decimal serialization/formatting.
10. Datetime serialization/formatting.
11. Pagination links/state preservation.
12. Detail route identity encoding.
13. Full-detail delegation.
14. Rendering None versus empty collections.
15. Evidence UUID display.
16. Empty database/no-results behavior.
17. Static CSS/assets approach.
18. Test strategy with FastAPI + real PostgreSQL.
19. Health endpoint regression.
20. Exact files to create/modify.
21. Whether any dependency, migration, or ADR is needed.
22. Overengineering risks.

Do not implement:
- ingestion controls
- charts/dashboard analytics
- signals/opportunities
- entity resolution
- auth/users
- exports
- raw evidence viewer
- frontend framework/build tooling
- natural-language/LLM search
- scheduler/workers

Return only the implementation plan.
```

## 15. Human review questions

- Does the UI reuse ProcurementQueries instead of SQL?
- Is server-rendered HTML enough?
- Is a frontend framework being introduced unnecessarily?
- Can a real user search and open a procurement?
- Are Decimal and missing-value semantics preserved?
- Is source independence visible in labels and routes?
- Is pagination usable without overengineering?
- Does the detail page show only current domain facts?
- Are signals/intelligence kept out until SPEC-011?
