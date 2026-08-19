# SPEC-004 — Raw Evidence Persistence Foundation

**Status:** Implemented  
**Milestone:** 1 — First Real Intelligence  
**Type:** Implementation  
**Depends on:** SPEC-001, SPEC-002, SPEC-003

## 1. Context

SPEC-003 introduced the first production source connector. The SERCOP connector can now return:

```text
typed source data
+
exact raw response bytes
+
retrieval provenance
```

Conceptually:

```python
result = await sercop.get_record(ocid="ocds-...")
result.data
result.raw_body
result.provenance
```

The application currently loses this information when the process ends.

Before implementing historical ingestion, domain normalization, procurement entities, or intelligence signals, Public Intelligence needs a durable persistence foundation for raw source evidence.

The raw layer must preserve source fidelity and allow future reprocessing.

This spec introduces that foundation using PostgreSQL.

## 2. Problem

Public Intelligence will eventually transform source data through multiple stages:

```text
Source
   ↓
Connector
   ↓
Raw Evidence
   ↓
Normalization
   ↓
Domain
   ↓
Events
   ↓
Signals
```

If only normalized data is persisted, information that appears unimportant today may be irreversibly lost.

Therefore the system needs a durable raw evidence store before normalization pipelines are built.

## 3. Goal

Implement a minimal persistence layer capable of storing and retrieving exact raw source responses and their provenance.

The persistence model must remain source-neutral enough to support future connectors such as SERCOP, RSU, ARCSA, and SUPERCIAS without introducing domain-specific interpretation.

Conceptual use:

```python
stored = await repository.save(evidence)
raw = await repository.get(stored.id)
assert raw.payload == original_raw_bytes
```

## 4. Non-goals

SPEC-004 does **not** implement:

- SERCOP bulk historical ingestion
- procurement normalization
- procurement domain entities
- company entities
- Public Intelligence events
- signals
- opportunities
- entity resolution
- scheduled jobs or polling
- deduplication workflows
- snapshot comparison
- historical change detection
- frontend or public API endpoints
- authentication or multi-tenancy
- AI/LLM functionality
- caching
- message brokers
- distributed/object storage
- data warehouse
- generic CRUD repository framework


## 5. Learning walkthrough

### 5.1 Source request

SPEC-003 can call:

```text
GET /api/record?ocid=ABC
```

and receive bytes such as:

```python
b'{"version":"1.1","releases":[...]}'
```

Those bytes are the evidence we want to preserve.

### 5.2 Connector result

Conceptually:

```python
SercopResult(
    data=SercopRecordPackage(...),
    raw_body=b'{"version":"1.1","releases":[...]}',
    provenance=SercopProvenance(
        source="sercop",
        mechanism="ocid_record",
        endpoint="/api/record",
        parameters={"ocid": "ABC"},
        retrieved_at=...,
        http_status=200,
        content_type="application/json",
        payload_sha256="...",
        payload_byte_size=...,
    ),
)
```

The typed DTO is convenient for software. The raw bytes are the original evidence. The provenance explains where the evidence came from.

### 5.3 Persist raw evidence

SPEC-004 introduces a source-neutral persistence representation:

```text
RawEvidence
├── id
├── source
├── mechanism
├── source_key
├── endpoint
├── parameters
├── retrieved_at
├── http_status
├── content_type
├── payload_sha256
├── payload_byte_size
├── payload
├── etag
├── last_modified
└── created_at
```

### 5.4 Future reprocessing

Later:

```text
RawEvidence
    ↓
ProcurementNormalizer
    ↓
Procurement domain model
```

If normalization changes, historical raw evidence can be processed again without querying the external source again.

## 6. Provenance

Provenance answers:

```text
Where did this data come from?
When did we retrieve it?
What request produced it?
What exact bytes did we receive?
How can we verify those bytes?
```

It supports reproducibility, debugging, audits, reprocessing, source comparisons, and future historical intelligence.


## 7. Architecture direction

Preferred conceptual flow:

```text
Connector
   ↓
Connector Result
   ├── typed source DTO
   ├── raw bytes
   └── source provenance
            ↓
     persistence boundary
            ↓
        PostgreSQL
```

The persistence layer must not depend directly on `SercopResult`.

Prefer a source-neutral input such as `RawEvidenceInput`.

## 8. Functional requirements

### FR-1 — PostgreSQL persistence

Add PostgreSQL as the project persistence technology. Local development must use a real PostgreSQL instance.

### FR-2 — Raw evidence storage

Create a persistence structure equivalent to `raw_evidence` containing at minimum:

- internal primary key
- source
- access mechanism
- optional source record key
- endpoint
- request parameters
- retrieval timestamp
- HTTP status
- content type
- payload SHA-256
- payload byte size
- exact payload bytes
- optional ETag
- optional Last-Modified
- created timestamp

### FR-3 — Exact payload preservation

If `payload = result.raw_body`, then after persistence and retrieval:

```python
loaded.payload == payload
```

must be true.

The persistence layer must not parse and reserialize the payload before storage.

### FR-4 — Payload storage type

Prefer PostgreSQL `BYTEA` for exact raw payload storage.

Do not use JSONB as the only representation of raw evidence.

### FR-5 — Request parameters

Persist request parameters in structured form, preferably PostgreSQL `JSONB`.

### FR-6 — Source-neutral input

Define a minimal source-neutral input model equivalent to:

```python
@dataclass(frozen=True)
class RawEvidenceInput:
    source: str
    mechanism: str
    source_key: str | None
    endpoint: str
    parameters: Mapping[str, object]
    retrieved_at: datetime
    http_status: int
    content_type: str
    payload_sha256: str
    payload_byte_size: int
    payload: bytes
    etag: str | None = None
    last_modified: str | None = None
```

### FR-7 — Persisted representation

Provide a persisted/read model `RawEvidence` or equivalent containing generated ID, persisted evidence/provenance fields, and created timestamp.

### FR-8 — Repository operations

Support at minimum:

```python
async def save(evidence: RawEvidenceInput) -> RawEvidence: ...
async def get(evidence_id: ...) -> RawEvidence | None: ...
```

Do not add generic CRUD abstractions.

### FR-9 — Internal identifier

Use a durable internal identifier, preferably UUID. Do not use OCID or another source identifier as the primary key.

### FR-10 — Source key

Persist an optional `source_key` separately from the internal ID, e.g. SERCOP OCID or future registration number.

### FR-11 — Timestamps

Persist `retrieved_at` and `created_at` as timezone-aware UTC timestamps.

### FR-12 — Integrity validation

Before persistence verify:

```text
SHA-256(payload) == declared payload_sha256
len(payload) == declared payload_byte_size
```

Reject mismatches; do not silently correct metadata.

### FR-13 — Database lifecycle

Use a clear async database connection/pool lifecycle independent of FastAPI.

### FR-14 — Schema migrations

Schema changes must be reproducible through explicit migrations. Do not create tables automatically during normal application startup.

### FR-15 — Local PostgreSQL

Document a reproducible local PostgreSQL workflow. Docker Compose is allowed because PostgreSQL is now a real infrastructure dependency.

If Compose is used, keep it to PostgreSQL only for this spec.


## 9. Idempotency and duplicates

SPEC-004 deliberately does not implement semantic deduplication.

If identical bytes are retrieved twice at different times, both observations may be stored.

Do not add a unique constraint solely on `payload_sha256`.

## 10. Open implementation questions

### OQ-1 — psycopg 3 vs SQLAlchemy 2 async

Evaluate which is simpler for this raw persistence layer.

Do not select an ORM merely because ORMs are common.

### OQ-2 — Migration tool

Recommend an explicit migration mechanism such as Alembic or a simpler tool compatible with the chosen DB access strategy.

### OQ-3 — Docker Compose

Determine the minimum PostgreSQL-only local setup.

### OQ-4 — UUID strategy

Evaluate UUIDv4 vs UUIDv7 if naturally supported. Do not add a dependency solely for UUIDv7 without concrete benefit.

### OQ-5 — Provenance ownership

Preferred default:

```text
leave connector provenance source-local
+
introduce persistence-specific RawEvidenceInput
```

Avoid refactoring SPEC-003 unless immediate reuse proves necessary.


## 11. Proposed package structure

Conceptually:

```text
src/public_intelligence/persistence/
├── __init__.py
├── database.py
└── raw_evidence/
    ├── __init__.py
    ├── models.py
    └── repository.py
```

Migration files may live in the migration tool's conventional location.

Do not create `BaseRepository`, `GenericRepository`, `UnitOfWork`, or domain repositories unless the current spec demonstrates an immediate need.

## 12. Testing strategy

### TR-1 — Real PostgreSQL

Persistence tests must exercise a real PostgreSQL database. Mocking SQL is insufficient for BYTEA, JSONB, timezone, migration, and constraint behavior.

### TR-2 — Test isolation

Tests must not depend on pre-existing developer data. Use the simplest reliable isolation strategy.

### TR-3 — Save and retrieve

Verify:

```python
saved = await repository.save(input)
loaded = await repository.get(saved.id)
```

and compare all fields.

### TR-4 — Exact bytes

Verify binary round-trip including non-ASCII UTF-8 bytes, whitespace differences, and newline differences.

### TR-5 — Hash and size invariants

Reject hash mismatch and byte-size mismatch.

### TR-6 — Parameters JSON

Verify request parameter round-trip.

### TR-7 — Timezones

Verify UTC-aware timestamps remain timezone-aware after retrieval.

### TR-8 — Duplicate observations

Store identical payload bytes twice with different retrieval timestamps and verify both rows exist.

### TR-9 — Source independence

Persist one synthetic second source such as `example_source` to prove raw persistence is not SERCOP-specific.

### TR-10 — Migration validation

Demonstrate migrations can create the schema from an empty PostgreSQL database.


## 13. Acceptance criteria

### Database

- [x] PostgreSQL is configured.
- [x] Local PostgreSQL startup is documented.
- [x] Database lifecycle is explicit.
- [x] Connections are pooled/reused appropriately.
- [x] Persistence code does not depend on FastAPI.

### Schema

- [x] A versioned migration creates raw evidence storage.
- [x] Internal ID is independent from source identity.
- [x] Source and mechanism are persisted.
- [x] Optional source key is persisted.
- [x] Endpoint and structured parameters are persisted.
- [x] Retrieved timestamp is timezone-aware.
- [x] HTTP status and content type are persisted.
- [x] SHA-256 and byte size are persisted.
- [x] Exact payload bytes are persisted.
- [x] ETag and Last-Modified are nullable.
- [x] Created timestamp is timezone-aware.
- [x] Payload hash is not globally unique.

### Persistence boundary

- [x] A source-neutral `RawEvidenceInput` or equivalent exists.
- [x] A persisted `RawEvidence` representation exists.
- [x] Repository supports save.
- [x] Repository supports get by internal ID.
- [x] No generic CRUD repository is introduced.
- [x] SERCOP DTOs are not persistence models.

### Integrity

- [x] SHA-256 is validated before persistence.
- [x] Payload byte size is validated before persistence.
- [x] Invalid metadata is rejected.
- [x] Exact payload bytes round-trip without modification.

### Tests

- [x] Tests use real PostgreSQL.
- [x] Tests are isolated from developer data.
- [x] Save/get behavior is tested.
- [x] Binary payload round-trip is tested.
- [x] Parameters round-trip is tested.
- [x] UTC timestamps are tested.
- [x] Duplicate identical payload observations are allowed.
- [x] Source-neutral behavior is tested.
- [x] Migration from empty database is validated.
- [x] Existing SPEC-001 and SPEC-003 tests still pass.

### Scope

- [x] No SERCOP bulk ingestion is implemented.
- [x] No procurement domain model is implemented.
- [x] No events or signals are implemented.
- [x] No entity resolution is implemented.
- [x] No public API endpoint is added.
- [x] No background worker is added.
- [x] No generic repository framework is introduced.

### Quality

- [x] dependency lockfile is consistent.
- [x] Ruff format passes.
- [x] Ruff lint passes.
- [x] mypy passes.
- [x] pytest passes.
- [x] migration validation passes.
- [x] git diff --check passes.

## 14. Definition of Done

SPEC-004 is complete when the application has a tested persistence boundary capable of receiving source-neutral raw evidence:

```text
raw bytes
+
provenance metadata
```

and storing it durably in PostgreSQL such that retrieved payload bytes are exactly equal to the original payload bytes.

A future spec should be able to use this boundary for SERCOP historical ingestion without changing its core semantics.


## 15. Suggested `/plan` prompt

```text
/plan

Read:

- AGENTS.md
- docs/vision.md
- docs/adr/ADR-001-modular-monolith.md
- docs/specs/README.md
- docs/specs/SPEC-001-project-foundation.md
- docs/specs/SPEC-002-sercop-data-source-research.md
- docs/specs/SPEC-003-sercop-targeted-connector.md
- src/public_intelligence/connectors/sercop/
- docs/specs/SPEC-004-raw-evidence-persistence-foundation.md

Plan the implementation of SPEC-004.

Do not modify files yet.

This spec introduces the first PostgreSQL persistence capability and must
remain limited to source-neutral raw evidence.

Your plan must explicitly address:

1. psycopg 3 vs SQLAlchemy 2 async and why.
2. Migration tooling and why.
3. PostgreSQL connection/pool lifecycle.
4. Minimal Docker Compose setup for local PostgreSQL.
5. Raw payload storage type and exact-byte preservation.
6. JSONB use for request parameters.
7. UUID strategy.
8. RawEvidenceInput and RawEvidence model design.
9. Repository public interface.
10. SHA-256 and byte-size validation.
11. Timezone handling.
12. Integration-test database isolation strategy.
13. How migrations will be validated from an empty database.
14. Exact dependencies to add.
15. Exact files expected to create or modify.
16. Any part of SPEC-004 that risks overengineering.

Do not implement:
- SERCOP bulk ingestion
- procurement domain entities
- events
- signals
- entity resolution
- FastAPI persistence endpoints
- background workers
- generic repository frameworks

Return only the implementation plan.
```

## 16. Questions for human review

When reviewing `/plan`, verify:

- Did Codex choose an ORM because it solves a current problem or merely because ORMs are common?
- Did it introduce a generic repository too early?
- Is raw payload truly byte-exact?
- Can two identical observations coexist?
- Are timestamps truly timezone-aware?
- Can this persistence layer accept future RSU data without knowing anything about RSU?
- Are migrations explicit and reproducible?
- Are integration tests exercising real PostgreSQL?
