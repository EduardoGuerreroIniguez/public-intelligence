# SPEC-007 — Normalized Procurement Persistence

**Status:** Implemented  
**Milestone:** 1 — First Real Intelligence  
**Type:** Implementation  
**Depends on:** SPEC-001 through SPEC-006

## 1. Context

Public Intelligence can now ingest SERCOP bulk partitions, persist raw evidence, validate SERCOP release packages, and map supported source data into a source-independent `ProcurementRecord` domain model.

The current flow is:

```text
RawEvidence
   ↓
SercopRecordPackage
   ↓
map_procurement_package()
   ↓
ProcurementRecord
```

`ProcurementRecord` currently exists only in memory.

SPEC-007 introduces normalized procurement persistence:

```text
ProcurementRecord
      ↓
normalized PostgreSQL persistence
      ↓
queryable procurement facts
```

Raw evidence remains the source of truth and must remain independently preserved.

## 2. Problem

Raw evidence is ideal for fidelity and reprocessing, but inefficient for business queries. Today, answering questions about buyers, suppliers, amounts, awards, or contracts requires decoding and remapping raw JSON repeatedly.

Normalized persistence should make factual procurement data queryable without coupling the database layer to SERCOP DTOs.

## 3. Goal

Persist supported `ProcurementRecord` objects into PostgreSQL using source-independent normalized tables.

The normalized representation must support:

- procurement identity by source + external ID;
- buyer facts;
- supplier facts;
- procedure facts;
- monetary values;
- awards;
- contracts;
- minimal evidence linkage;
- deterministic reprocessing/upsert behavior.

SPEC-007 does not introduce signals, events, entity resolution, or analytics APIs.

## 4. Non-goals

Do **not** implement:

- entity resolution;
- company master data;
- signals/opportunities;
- domain events;
- normalized historical version tables;
- schedulers/workers/queues;
- APIs;
- dashboards;
- search engine/indexing;
- full OCDS persistence;
- currency conversion;
- fuzzy organization matching;
- ORM/generic repository frameworks;
- reporting warehouse/star schema.

## 5. Learning walkthrough

### 5.1 Raw vs normalized

Raw answers:

> What exactly did the source give us?

Normalized answers:

> What factual procurement information did we extract?

Example:

```text
raw_evidence.payload
      ↓ mapper
ProcurementRecord
      ↓ repository
procurements + child tables
```

### 5.2 Why multiple tables?

A procurement contains nested collections:

```text
ProcurementRecord
├── buyer
├── suppliers[]
├── procedure
├── awards[]
└── contracts[]
```

Flattening everything into one table would duplicate parent data across combinations of suppliers, awards, and contracts.

### 5.3 Normalization is not entity resolution

Persisting:

```text
buyer_external_id = X
buyer_name = MUNICIPIO X
```

means:

> this procurement snapshot references this organization as supplied by the source.

It does **not** mean we have resolved that organization against Supercias, RSU, or another source.

## 6. Architectural principles

Dependency direction:

```text
procurement domain
      ↓
normalized persistence
      ↓
PostgreSQL
```

The repository may depend on domain models.

The domain must not depend on persistence.

The repository must not accept SERCOP DTOs.

Correct:

```python
await repository.save(record: ProcurementRecord)
```

Incorrect:

```python
await repository.save(package: SercopRecordPackage)
```

## 7. Persistence strategy

Reuse:

- PostgreSQL;
- Psycopg 3;
- async connection pool;
- Yoyo migrations.

Do not introduce SQLAlchemy.

## 8. Expected relational concepts

The exact schema is subject to `/plan`, but expected normalized structures are approximately:

```text
procurements
procurement_suppliers
procurement_awards
award_suppliers
procurement_contracts
```

Do not automatically introduce a master `organizations` table.

## 9. Functional requirements

### FR-1 — Procurement identity

A procurement is uniquely identified by:

```text
(source, external_id)
```

Example:

```text
sercop + ocds-123
```

Do not treat OCID alone as globally unique.

### FR-2 — Internal ID

Use an internal UUID primary key for normalized procurement rows.

Add:

```text
UNIQUE(source, external_id)
```

Repeated processing of the same procurement must not create a new logical normalized procurement.

### FR-3 — Evidence linkage

Persist the raw-evidence UUID used to produce the normalized snapshot.

Preferred design:

```text
evidence_id UUID REFERENCES raw_evidence(id)
```

Default delete behavior: `RESTRICT`, unless `/plan` justifies otherwise.

Do not copy payload bytes or raw provenance JSON into normalized tables.

### FR-4 — Snapshot semantics

Persist one current normalized snapshot per `(source, external_id)`.

Raw evidence history remains separate.

Do not create normalized historical version rows in SPEC-007.

### FR-5 — Upsert behavior

Saving the same procurement identity again must update the normalized snapshot deterministically.

Requirements:

- preserve stable internal procurement UUID where practical;
- update evidence reference;
- update parent scalar fields;
- replace child collections;
- remove stale children;
- perform the whole replacement atomically.

`updated_at` means the last successful persistence/reprocessing time of the
normalized snapshot. Every successful save refreshes it, including when the
persisted snapshot is semantically identical; it does not necessarily indicate
that procurement data changed.

### FR-6 — Buyer persistence

Prefer procurement-scoped columns:

```text
buyer_external_id
buyer_name
```

Missing buyer remains NULL.

Do not create a buyer master table.

### FR-7 — Procedure persistence

Persist only fields present in the implemented SPEC-006 `ProcurementProcedure` model.

Likely fields include:

- external procedure ID;
- title;
- description;
- status;
- method;
- method details;
- category;
- value amount;
- value currency.

The `/plan` must use exact implemented names.

### FR-8 — Money

Use PostgreSQL `NUMERIC`, never float/double.

Missing Money:

```text
amount = NULL
currency = NULL
```

Explicit zero remains numeric zero.

Currency remains nullable and is never inferred.

### FR-9 — Procurement suppliers

Persist procurement-level suppliers in a child table.

Suggested fields:

```text
procurement_id
ordinal
external_id
name
```

Preserve tuple order.

The `/plan` must explicitly preserve `None` vs `()` only if the SPEC-006 domain actually distinguishes those states.

### FR-10 — Awards

Persist awards in a child table with only SPEC-006 domain fields.

Expected fields:

- procurement FK;
- ordinal;
- external award ID;
- status;
- date;
- value amount/currency.

### FR-11 — Award suppliers

Persist award supplier associations separately so award-specific supplier relationships are not lost.

Do not assume procurement-level suppliers replace award-level supplier facts.

### FR-12 — Contracts

Persist contracts in a child table with only SPEC-006 fields.

Expected fields:

- procurement FK;
- ordinal;
- external contract ID;
- external award reference;
- status;
- date signed;
- value amount/currency.

Do not infer award linkage.

### FR-13 — Datetimes

Persist domain datetimes using `TIMESTAMPTZ`.

Domain values are expected to be UTC-aware from SPEC-006.

### FR-14 — Repository boundary

Introduce a small source-independent repository, conceptually:

```python
class ProcurementRepository:
    async def save(self, record: ProcurementRecord) -> StoredProcurement: ...

    async def get(self, source: str, external_id: str) -> ProcurementRecord | None: ...
```

The `/plan` must decide whether save returns an internal-ID wrapper or minimal metadata.

Avoid generic CRUD abstractions.

### FR-15 — Atomic replacement

One save operation must use one DB transaction:

```text
BEGIN
  upsert procurement
  replace procurement suppliers
  replace awards
  replace award suppliers
  replace contracts
COMMIT
```

Any child failure must roll back the complete new snapshot.

### FR-16 — Reprocessing safety

Given the same `ProcurementRecord` twice:

```python
await repo.save(record)
await repo.save(record)
```

normalized state must remain equivalent with no duplicate children.

### FR-17 — Changed snapshot replacement

If a later record with the same identity changes buyer/procedure/suppliers/awards/contracts/evidence ID, the normalized state must exactly reflect the later record.

Stale child rows must be removed.

### FR-18 — No source-specific repository

Do not create `SercopProcurementRepository`.

### FR-19 — No normalized history yet

Do not create:

```text
procurement_versions
procurement_history
procurement_events
```

Raw evidence already preserves historical source observations.

## 10. Suggested schema direction

Conceptual parent table:

```text
procurements
------------
id UUID PK
source TEXT NOT NULL
external_id TEXT NOT NULL
evidence_id UUID NULL/NOT NULL per approved domain semantics
buyer_external_id TEXT NULL
buyer_name TEXT NULL
procedure_external_id TEXT NULL
title TEXT NULL
description TEXT NULL
status TEXT NULL
method TEXT NULL
method_details TEXT NULL
category TEXT NULL
value_amount NUMERIC NULL
value_currency TEXT NULL
created_at TIMESTAMPTZ NOT NULL
updated_at TIMESTAMPTZ NOT NULL

UNIQUE(source, external_id)
```

Children:

```text
procurement_suppliers
procurement_awards
award_suppliers
procurement_contracts
```

The `/plan` must refine this against actual SPEC-006 dataclasses.

## 11. Migration requirements

Add a new versioned migration after raw evidence.

Do not modify migration 0001.

Migration sequence from empty DB must succeed:

```text
0001 raw_evidence
↓
0002 normalized procurement
```

Rollback must remove only SPEC-007 structures and preserve `raw_evidence`.

## 12. Testing strategy

### TR-1 — Real PostgreSQL

Use the disposable real-PostgreSQL infrastructure already established.

### TR-2 — Migration

Validate full migration sequence from empty DB, expected tables/constraints/FKs/types, and no pending migrations.

### TR-3 — Domain round-trip

Save a `ProcurementRecord`, retrieve it, and assert domain equality.

### TR-4 — Evidence linkage

If FK is approved:

- valid evidence ID succeeds;
- missing evidence ID behaves according to the domain contract;
- nonexistent evidence ID fails;
- delete behavior is tested.

### TR-5 — Buyer

Round-trip buyer present and buyer=None.

### TR-6 — Money

Test Decimal precision, zero, missing amount, nullable currency, and no float conversion.

### TR-7 — Suppliers

Test absent/empty/non-empty states where supported, plus one/multiple suppliers and stable order.

### TR-8 — Awards

Test none/empty/non-empty according to actual domain semantics.

### TR-9 — Award suppliers

Verify association and ordering survive round-trip.

### TR-10 — Contracts

Test optional fields, award external reference, date/value.

### TR-11 — Idempotent save

Save identical record twice and verify one logical procurement with no duplicate children.

### TR-12 — Changed snapshot

Save A, then changed B with the same identity. Verify parent and child state exactly match B and stale child rows are removed.

### TR-13 — Atomic rollback

Force a child persistence failure and verify no partial replacement occurs.

### TR-14 — Source independence

Persist a synthetic `ProcurementRecord` with `source="example_source"`.

### TR-15 — Existing suite

All SPEC-001 through SPEC-006 tests remain green. No live SERCOP required.

## 13. Open design questions for `/plan`

Resolve explicitly:

1. exact schema from actual SPEC-006 dataclasses;
2. None-vs-empty collection persistence;
3. parent UUID strategy;
4. evidence FK and ON DELETE behavior;
5. child PK strategy: UUID vs `(parent_id, ordinal)`;
6. upsert algorithm;
7. atomic child replacement strategy;
8. repository save/get return types;
9. domain reconstruction from SQL;
10. created_at/updated_at behavior;
11. NUMERIC precision declaration vs unconstrained NUMERIC;
12. indexes beyond business-key uniqueness;
13. rollback semantics;
14. migration/rollback files.

Default preference:

```text
explicit SQL
+
minimal schema
+
no speculative indexes
+
no master organization table
```

## 14. Acceptance criteria

### Architecture

- [x] Normalized persistence depends on procurement domain, not SERCOP.
- [x] Procurement domain remains persistence-independent.
- [x] Existing PostgreSQL/Psycopg/Yoyo stack is reused.
- [x] No ORM/generic repository framework is introduced.

### Schema

- [x] Versioned migration creates normalized procurement structures.
- [x] Raw evidence schema remains intact.
- [x] Procurement internal UUID exists.
- [x] `(source, external_id)` is unique.
- [x] Evidence linkage is persisted.
- [x] Buyer is procurement-scoped.
- [x] Procedure fields match the domain only.
- [x] Monetary amounts use NUMERIC.
- [x] Currency remains nullable.
- [x] Procurement suppliers are normalized.
- [x] Awards are normalized.
- [x] Award suppliers retain award association.
- [x] Contracts are normalized.
- [x] Timestamps use TIMESTAMPTZ.
- [x] No master organization/entity-resolution table exists.

### Repository

- [x] Source-independent ProcurementRepository exists.
- [x] save accepts ProcurementRecord.
- [x] get reconstructs normalized procurement data.
- [x] No SERCOP DTO enters the repository.
- [x] Save is atomic.
- [x] Re-saving same identity does not duplicate children.
- [x] Changed snapshot replaces stale children.
- [x] Evidence reference updates during replacement.
- [x] No normalized history/version table is introduced.

### Fidelity

- [x] Missing buyer remains missing.
- [x] Missing money differs from zero.
- [x] Decimal never passes through float.
- [x] Currency is never inferred.
- [x] Supplier ordering is deterministic.
- [x] Award supplier associations are preserved.
- [x] Contract award reference is not inferred.
- [x] Domain source/external identity round-trips exactly.

### Tests

- [x] Tests use real disposable PostgreSQL.
- [x] Full migrations apply from empty DB.
- [x] Domain round-trip is tested.
- [x] Evidence integrity/FK behavior is tested if applicable.
- [x] Buyer optionality is tested.
- [x] Money precision/zero/missing/currency are tested.
- [x] Supplier states/order are tested.
- [x] Awards/award suppliers are tested.
- [x] Contracts are tested.
- [x] Idempotent repeated save is tested.
- [x] Changed snapshot replacement is tested.
- [x] Atomic rollback is tested.
- [x] Synthetic second source proves source independence.
- [x] Existing SPEC-001 through SPEC-006 tests pass.

### Scope

- [x] No entity resolution.
- [x] No company master.
- [x] No signals/opportunities.
- [x] No domain events.
- [x] No scheduler/worker/queue.
- [x] No API.
- [x] No normalized historical versioning.
- [x] No analytics warehouse.
- [x] No full OCDS persistence.

### Quality

- [x] No unnecessary dependencies.
- [x] lockfile consistent.
- [x] Ruff format/lint pass.
- [x] mypy passes.
- [x] pytest passes.
- [x] migration validation passes.
- [x] git diff --check passes.

## 15. Definition of Done

SPEC-007 is complete when a source-independent `ProcurementRecord` can be persisted as a normalized PostgreSQL snapshot and later reconstructed faithfully, while retaining traceability to the raw evidence used to produce it.

```text
RawEvidence
    ↓
SERCOP DTO
    ↓
ProcurementRecord
    ↓
ProcurementRepository
    ↓
normalized PostgreSQL
```

Repeated processing of the same procurement identity must safely update the normalized snapshot without duplicate children or loss of raw-evidence history.

## 16. Suggested `/plan` prompt

```text
/plan

Read:

- AGENTS.md
- docs/vision.md
- docs/adr/ADR-001-modular-monolith.md
- docs/adr/ADR-002-postgresql-raw-evidence-persistence.md
- docs/specs/SPEC-004-raw-evidence-persistence-foundation.md
- docs/specs/SPEC-005-sercop-historical-bulk-ingestion.md
- docs/specs/SPEC-006-procurement-domain-mapping.md
- src/public_intelligence/domain/procurement/
- src/public_intelligence/persistence/
- migrations/
- tests/persistence/
- docs/specs/SPEC-007-normalized-procurement-persistence.md

Plan SPEC-007. Do not modify files.

Explicitly address:

1. Exact PostgreSQL schema mapped from actual SPEC-006 domain dataclasses.
2. Procurement parent columns.
3. Buyer representation.
4. Procedure representation.
5. Money NUMERIC strategy.
6. Procurement supplier schema and None-vs-empty preservation.
7. Award schema.
8. Award supplier schema and collection semantics.
9. Contract schema.
10. Internal UUID and `(source, external_id)` uniqueness.
11. RawEvidence evidence FK and ON DELETE behavior.
12. Child PK strategy: UUID vs parent+ordinal.
13. Atomic upsert/replacement algorithm.
14. Stable internal procurement ID on repeated save.
15. Repository save/get public interface.
16. Domain reconstruction from SQL rows.
17. created_at/updated_at behavior.
18. Transaction rollback semantics.
19. Migration and rollback files.
20. Migration-from-empty testing.
21. Exact integration tests.
22. Exact files to create/modify.
23. Whether any dependency/ADR is required.
24. Overengineering risks.

Do not implement entity resolution, organization master data, signals,
events, opportunities, normalized history/version tables, APIs,
workers/schedulers, generic repositories, ORM, or full OCDS persistence.

Return only the implementation plan.
```

## 17. Human review questions

- Is normalized persistence truly source-independent?
- Is a master organizations table being introduced too early?
- Can the same procurement be reprocessed safely?
- Are stale child rows removed on replacement?
- Does evidence linkage remain intact?
- Does Decimal remain Decimal into PostgreSQL?
- Are None/empty semantics preserved only where the domain distinguishes them?
- Is the transaction boundary strong enough to avoid half-updated snapshots?
- Are we persisting only fields justified in SPEC-006?
