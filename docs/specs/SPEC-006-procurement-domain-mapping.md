# SPEC-006 — Procurement Domain Mapping

**Status:** Implemented  
**Milestone:** 1 — First Real Intelligence  
**Type:** Implementation  
**Depends on:** SPEC-001, SPEC-002, SPEC-003, SPEC-004, SPEC-005

## 1. Context

Public Intelligence can now query SERCOP, ingest one bounded historical bulk partition, preserve exact bulk artifacts and canonical release-package evidence, and store source-neutral raw evidence with provenance in PostgreSQL.

The system still does not understand procurement as a business domain. PostgreSQL can hold an OCID and raw/canonical JSON bytes, but future analytics should not need to understand SERCOP JSON directly.

SPEC-006 introduces the first normalized, source-independent procurement representation.

```text
SERCOP RawEvidence
      ↓
validated SERCOP DTO
      ↓
SERCOP procurement mapper
      ↓
ProcurementRecord
```

This spec defines the domain and mapping only. It does not persist normalized procurement records.

## 2. Problem

Raw evidence is intentionally source-faithful, but raw source structures are poor application boundaries.

If future analytics/signals depend directly on SERCOP JSON:

```text
SERCOP schema = Public Intelligence domain
```

The intended architecture is:

```text
SERCOP source model
      ↓
source-specific mapper
      ↓
source-independent procurement domain
```

The domain must not depend on SERCOP, PostgreSQL, HTTP, FastAPI, or connector DTOs.

## 3. Goal

Implement:

- a minimal procurement domain model;
- a deterministic SERCOP-to-domain mapper;
- explicit mapping errors for unsupported/ambiguous source structures;
- tests grounded in existing SPEC-002/003/005 evidence.

The mapper must preserve uncertainty rather than inventing values.

## 4. Non-goals

Do not implement:

- normalized PostgreSQL tables/repositories;
- entity resolution;
- company master records;
- events;
- signals/opportunities;
- scoring/ML/AI;
- historical change detection;
- schedulers/workers/queues;
- API endpoints;
- search/indexing;
- dashboards;
- full OCDS modeling;
- generic mapper/domain frameworks;
- currency conversion.

## 5. Learning walkthrough

### 5.1 Source model vs domain model

Source:

```json
{
  "releases": [{
    "ocid": "ocds-123",
    "buyer": {...},
    "parties": [...],
    "tender": {...},
    "awards": [...],
    "contracts": [...]
  }]
}
```

Internal domain:

```text
ProcurementRecord
├── source reference
├── buyer
├── suppliers
├── procedure/tender facts
├── monetary facts
├── awards
└── contracts
```

### 5.2 Normalization is translation, not inference

If SERCOP provides a buyer ID/name, map them.

If currency is missing, keep:

```python
currency = None
```

Do not infer USD just because the procurement is Ecuadorian.

### 5.3 Normalization vs entity resolution

Normalization:

```text
{"id":"EC-RUC-...","name":"MUNICIPIO X"}
        ↓
OrganizationRef(external_id=..., name=...)
```

Entity resolution is a later problem:

```text
Is this SERCOP organization the same real-world entity
as a Supercias/RSU organization?
```

SPEC-006 does not solve that.

## 6. Domain design principles

The procurement domain must:

1. live under `public_intelligence.domain`;
2. import no SERCOP connector models;
3. import no persistence models;
4. know nothing about PostgreSQL/HTTP/FastAPI;
5. use immutable/value-oriented models;
6. preserve optionality honestly;
7. distinguish identifiers from display names;
8. remain minimal;
9. model facts, not interpretations.

## 7. Expected domain concepts

The `/plan` must justify the exact set, but expected minimal concepts include:

```text
ProcurementRecord
SourceReference
OrganizationRef
ProcurementProcedure
Money
Award
Contract
```

Only introduce concepts supported by observed evidence.

## 8. Functional requirements

### FR-1 — Procurement identity

Represent source-independent procurement identity.

Prefer:

```python
SourceReference(source="sercop", external_id="ocds-...")
```

Do not name a generic domain field `ocid`.

Do not introduce a generic identity framework.

### FR-2 — OrganizationRef

Minimal candidate:

```python
@dataclass(frozen=True, slots=True)
class OrganizationRef:
    external_id: str | None
    name: str | None
```

Do not claim an identifier is a validated RUC unless evidence supports that.

### FR-3 — Buyer

Map buyer facts only where present and supported.

The `/plan` must decide whether buyer is optional in `ProcurementRecord` based on existing fixtures.

### FR-4 — Suppliers

Map suppliers only from supported source locations.

No fuzzy matching or entity resolution.

Deduplicate only when exact deterministic equality is justified.

### FR-5 — Procedure/tender facts

Model only useful observed fields, potentially:

- title;
- description;
- procurement method/type;
- status;
- relevant dates;
- classifications.

The `/plan` must cite SPEC-002/fixtures for every selected field.

Do not copy the entire tender source object.

### FR-6 — Money

If modeled:

```python
@dataclass(frozen=True, slots=True)
class Money:
    amount: Decimal
    currency: str | None
```

Rules:

- use Decimal, never float;
- missing != zero;
- do not infer currency;
- invalid numeric source values fail explicitly if required for mapping.

### FR-7 — Awards

Model only supported factual fields, candidate minimum:

- external ID;
- status;
- date;
- value;
- suppliers.

Do not recreate full OCDS award objects.

### FR-8 — Contracts

Model only supported factual fields, candidate minimum:

- external contract ID;
- award reference when source evidence exists;
- status;
- date/value where supported.

Do not infer award linkage.

### FR-9 — Minimal provenance pointer

The domain may carry a minimal immutable source/evidence reference, such as:

```python
evidence_id: UUID | None
```

or equivalent.

Do not embed:

- RawEvidence;
- payload bytes;
- HTTP status;
- endpoint URL;
- request parameters.

### FR-10 — Mapper boundary

Implement one SERCOP-specific mapper conceptually equivalent to:

```python
class SercopProcurementMapper:
    def map(...) -> ProcurementRecord:
        ...
```

The mapper may depend on SERCOP DTOs and domain models.

Domain models must never depend on SERCOP.

### FR-11 — Mapper input

Consume already validated SERCOP DTOs or equivalent validated source representation.

The mapper performs no HTTP and no database access.

### FR-12 — Release-package identity ambiguity

Explicitly handle:

- zero releases;
- one release;
- multiple releases sharing one OCID;
- multiple distinct OCIDs.

Never silently choose the first distinct identity.

### FR-13 — Same-OCID multiple releases

Do not merge conflicting releases without an evidence-backed deterministic rule.

The `/plan` must choose between:

- supported deterministic selection;
- supported aggregation;
- explicit rejection for SPEC-006.

Prefer correctness and bounded scope.

### FR-14 — Mapping errors

Provide a small explicit mapper error design covering at least:

- missing/unusable procurement identity;
- ambiguous procurement identity;
- unsupported release structure;
- invalid monetary representation where relevant.

Do not create a broad validation framework.

### FR-15 — No normalized persistence

Do not create tables/repositories for procurements, organizations, awards, or contracts.

### FR-16 — Developer demonstration

Provide a test or documented example demonstrating:

```text
persisted package RawEvidence
      ↓
decode canonical JSON
      ↓
SercopRecordPackage validation
      ↓
SercopProcurementMapper
      ↓
ProcurementRecord
```

A production CLI is not required unless the `/plan` proves it necessary.

## 9. Mapping fidelity rules

1. Never invent currency, buyer, supplier, status, date, zero amount, or source identifier.
2. Do not globally normalize all empty strings to None unless justified per field.
3. Use Decimal for money.
4. Prefer strings over premature enums unless a stable domain enum is clearly justified.
5. Preserve external source identifiers; do not replace them with generated IDs.

## 10. Package structure

Conceptual direction:

```text
src/public_intelligence/
├── domain/
│   └── procurement/
│       ├── __init__.py
│       ├── models.py
│       └── errors.py
└── connectors/
    └── sercop/
        └── procurement_mapper.py
```

The `/plan` may choose a nearby source-adapter package if cleaner.

Dependency direction must remain:

```text
SERCOP mapper → procurement domain
procurement domain → nothing source-specific
```

Avoid `GenericMapper`, `BaseMapper`, registries, or `domain/sercop.py`.

## 11. Testing strategy

- Pure domain tests require no DB/network.
- Mapper tests make no live SERCOP calls.
- Reuse existing committed fixtures where practical.
- Test valid single OCID.
- Test blank OCID.
- Test distinct-OCID ambiguity.
- Test approved same-OCID multi-release policy.
- Test buyer present/missing.
- Test one/multiple/missing suppliers as supported.
- Test Decimal money, missing money, explicit zero, invalid numeric representation, known/missing currency.
- Test modeled award/contract fields and optional sections.
- Test unknown additive source fields.
- Instantiate domain models without SERCOP dependencies.
- All SPEC-001 through SPEC-005 tests remain green.

## 12. Acceptance criteria

### Domain boundary

- [x] Procurement domain package exists under `public_intelligence.domain`.
- [x] Domain imports no SERCOP connector models.
- [x] Domain imports no persistence models.
- [x] Domain knows nothing about HTTP/FastAPI/PostgreSQL.
- [x] Domain models are immutable/value-oriented.
- [x] No generic domain framework exists.

### Procurement model

- [x] Minimal ProcurementRecord exists.
- [x] Generic procurement identity is not named `ocid`.
- [x] Buyer and suppliers are minimally represented.
- [x] Procedure/tender facts are modeled only where supported.
- [x] Monetary values use Decimal where modeled.
- [x] Missing amount differs from zero.
- [x] Currency is not inferred.
- [x] Awards/contracts are modeled only to supported depth.

### Mapping

- [x] SERCOP-specific mapper translates validated source data into domain objects.
- [x] Mapper performs no HTTP/database access.
- [x] Mapper does not persist normalized data.
- [x] Blank identity is rejected.
- [x] Distinct-OCID ambiguity is explicit.
- [x] Same-OCID multi-release behavior is explicit.
- [x] Unsupported structures fail explicitly.
- [x] Additive unknown source fields are tolerated where safe.
- [x] No source facts/currency are invented.
- [x] No float money is introduced.

### Provenance/reference

- [x] Minimal source/evidence reference can be preserved without depending on RawEvidence.
- [x] Raw payload and HTTP metadata are not embedded in the domain.

### Tests

- [x] Domain tests require no DB/network.
- [x] Mapper tests require no live SERCOP.
- [x] Existing fixtures are reused where practical.
- [x] Identity ambiguity is tested.
- [x] Buyer/supplier optionality is tested.
- [x] Money mapping/invalid money are tested.
- [x] Awards/contracts are tested only to modeled depth.
- [x] Additive source fields remain safe.
- [x] Source-independent domain construction is tested.
- [x] Existing SPEC-001 through SPEC-005 tests pass.

### Scope

- [x] No normalized DB tables/repositories.
- [x] No entity resolution.
- [x] No domain events/signals/opportunities.
- [x] No scheduler/worker/queue.
- [x] No API endpoint.
- [x] No full OCDS model.
- [x] No generic mapper framework.

### Quality

- [x] No unnecessary dependencies.
- [x] lockfile consistent.
- [x] Ruff format/lint pass.
- [x] mypy passes.
- [x] pytest passes.
- [x] git diff --check passes.

## 13. Definition of Done

SPEC-006 is complete when a supported validated SERCOP release package can be deterministically translated into a minimal source-independent `ProcurementRecord` representing factual procurement information without inventing values, coupling the domain to SERCOP, persisting normalized data, or generating signals/events.

```text
SERCOP evidence
      ↓
validated source DTO
      ↓
SERCOP mapper
      ↓
ProcurementRecord
```

## 14. Suggested `/plan` prompt

```text
/plan

Read:

- AGENTS.md
- docs/vision.md
- docs/adr/ADR-001-modular-monolith.md
- docs/adr/ADR-002-postgresql-raw-evidence-persistence.md
- docs/specs/SPEC-002-sercop-data-source-research.md
- docs/research/sercop/
- docs/specs/SPEC-003-sercop-targeted-connector.md
- docs/specs/SPEC-004-raw-evidence-persistence-foundation.md
- docs/specs/SPEC-005-sercop-historical-bulk-ingestion.md
- src/public_intelligence/connectors/sercop/
- src/public_intelligence/persistence/
- src/public_intelligence/domain/
- docs/specs/SPEC-006-procurement-domain-mapping.md

Plan SPEC-006. Do not modify files.

Explicitly address:

1. Exact ProcurementRecord fields and fixture/research evidence for each.
2. OrganizationRef design.
3. Source-independent procurement identity.
4. Release package vs release mapping unit.
5. Zero-release policy.
6. Same-OCID multi-release policy.
7. Distinct-OCID policy.
8. Buyer optionality.
9. Supplier extraction/deduplication.
10. Money with Decimal and no inferred currency.
11. Exact award fields.
12. Exact contract fields.
13. Strings vs enums for statuses/methods.
14. Minimal source/evidence reference.
15. Mapper location/dependency direction.
16. Whether a raw-evidence-to-DTO helper is needed.
17. Mapping errors.
18. Tests/fixtures to reuse.
19. Exact files to create/modify.
20. New dependency/ADR need.
21. Overengineering risks.

Do not implement normalized persistence, entity resolution, events, signals,
opportunities, workers, APIs, generic mapping frameworks, or full OCDS.

Return only the implementation plan.
```

## 15. Human review questions

- Is every domain field justified by observed source evidence?
- Would the domain still make sense if SERCOP were replaced?
- Are we confusing normalization with entity resolution?
- Are missing values becoming guesses?
- Does Money distinguish missing, zero, and invalid?
- Are multiple releases merged without evidence?
- Can future sources reuse OrganizationRef without knowing SERCOP?
- Is the mapper the only boundary that knows both SERCOP and the domain?
