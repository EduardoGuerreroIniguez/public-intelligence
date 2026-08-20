# SPEC-005 — SERCOP Historical Bulk Ingestion

**Status:** Implemented  
**Milestone:** 1 — First Real Intelligence  
**Type:** Implementation  
**Depends on:** SPEC-001, SPEC-002, SPEC-003, SPEC-004

## 1. Context

Public Intelligence can now:

1. query SERCOP through the targeted connector;
2. preserve exact source responses and provenance;
3. persist source-neutral raw evidence in PostgreSQL.

SPEC-002 concluded that SERCOP bulk JSON is the preferred candidate for historical ingestion because it preserves richer nested source structures than flattened CSV/XLSX representations.

SPEC-005 introduces the first historical ingestion workflow.

```text
SERCOP bulk partition
        ↓
download
        ↓
capture artifact provenance
        ↓
extract source records
        ↓
RawEvidenceInput
        ↓
RawEvidenceRepository
        ↓
PostgreSQL
```

This spec does not normalize procurement concepts and does not generate domain events or signals.

## 2. Problem

Targeted API access is useful for interactive search and exact OCID lookup, but it is not an appropriate mechanism for building a historical corpus.

Historical intelligence requires a repeatable way to ingest bounded SERCOP bulk partitions while preserving where the data came from, which partition was requested, the source artifact, individual source units, ingestion outcome, and failures.

## 3. Goal

Implement a bounded SERCOP historical bulk-ingestion workflow capable of processing one explicitly requested partition at a time.

Conceptual API:

```python
result = await ingest_partition(
    year=2025,
    month=1,
    procurement_type="...",
)
```

The workflow should:

1. resolve the official bulk artifact for the requested partition;
2. download it using responsible HTTP behavior;
3. preserve artifact provenance;
4. parse the supported JSON publication shape;
5. convert each ingestible source unit into `RawEvidenceInput`;
6. persist raw evidence through the SPEC-004 repository;
7. return an ingestion summary.

No normalization into Public Intelligence procurement entities occurs in this spec.

## 4. Non-goals

SPEC-005 does **not** implement:

- procurement domain entities
- normalized procurement tables
- buyer/supplier entity resolution
- company intelligence
- events
- signals
- opportunities
- automatic scheduling
- background workers
- queues/message brokers
- distributed ingestion
- concurrent partition fan-out
- full-history backfill
- retry frameworks
- checkpoint frameworks
- web/API endpoints
- ingestion UI
- CSV/XLSX production ingestion
- generic bulk-ingestion frameworks
- data warehouse/object storage
- semantic deduplication across source records

## 5. Learning walkthrough

### 5.1 What is a partition?

Instead of requesting all SERCOP history at once, bulk data is approached in bounded slices such as:

```text
year + month + procurement type
```

Example:

```text
2025 + January + Direct Purchase
```

This bounded slice is a **partition**.

### 5.2 Artifact versus record

A bulk download is an artifact:

```text
bulk file
├── process A
├── process B
├── process C
└── ...
```

Artifact provenance describes the downloaded file itself.

Record provenance describes each individual source unit persisted into `raw_evidence`.

### 5.3 Why RawEvidence still matters

Even if the artifact contains JSON, this spec does not normalize procurement yet.

```text
source record bytes
       ↓
RawEvidenceInput
       ↓
raw_evidence
```

Future specs will normalize these rows into domain concepts.

## 6. Architectural principles

Preferred separation:

```text
connectors/sercop/
    bulk source access

pipelines/
    orchestration

persistence/
    raw evidence storage
```

Do not put ingestion orchestration in the repository. Do not put SQL in the SERCOP connector. Do not introduce domain logic.

## 7. Functional requirements

### FR-1 — Partition model

Define a SERCOP-specific partition model equivalent to:

```python
@dataclass(frozen=True, slots=True)
class SercopBulkPartition:
    year: int
    month: int
    procurement_type: str
```

Validate only obvious source-supported invariants.

### FR-2 — Bulk artifact discovery

Implement the smallest SERCOP-specific mechanism needed to resolve the official artifact for one requested partition, based on SPEC-002 research.

Do not crawl unrelated pages, guess private endpoints, or access authenticated SOCE functionality.

### FR-3 — Production format

Support JSON only in SPEC-005.

### FR-4 — HTTP behavior

Use async HTTP, explicit timeout, descriptive User-Agent, responsible request behavior, no automatic aggressive retries, and no concurrent partition downloads.

The `/plan` must decide streamed vs buffered download based on the observed packaging.

**Approved implementation decision:** SPEC-005 buffers one explicitly requested
artifact as a bounded proof of capability. The maximum size of real SERCOP
partitions is unknown, and this decision does not establish production
scalability. Streaming infrastructure and size-policy frameworks remain out of
scope unless immediate implementation evidence makes them necessary.

### FR-5 — Artifact provenance

Capture at minimum:

- source = `sercop`
- mechanism = `bulk_partition`
- year/month/procurement type
- resolved URL/path
- retrieval timestamp UTC
- HTTP status
- content type
- filename when available
- ETag / Last-Modified when available
- artifact SHA-256
- artifact byte size

### FR-6 — Artifact preservation strategy

Preserve the artifact during processing and compute checksum/size over the exact downloaded bytes.

Whether the artifact is permanently stored is left to `/plan`.

Do not introduce object storage.

### FR-7 — Supported bulk JSON shape

Parse only the bulk JSON/archive shape established by SPEC-002 evidence.

Do not implement a generic OCDS bulk parser.

### FR-8 — Ingestion unit

The `/plan` must identify the smallest meaningful source unit that should become one `RawEvidence` row.

The choice must be justified by source evidence, not convenience.

### FR-9 — Record raw bytes

For each source unit, generate deterministic raw bytes from the actual bulk source content.

If extraction requires serialization, use one deterministic strategy and document it.

Do not claim these bytes are identical to an independent API response.

The `bulk_partition` evidence row contains the exact downloaded ZIP response
bytes. `bulk_partition_release_package` rows contain deterministic canonical
JSON derived from the ZIP member; those bytes are neither the original HTTP
response bytes nor exact byte slices of the ZIP artifact.

### FR-10 — Record provenance

Each persisted `RawEvidenceInput` must include:

- source = `sercop`
- mechanism identifying bulk ingestion
- source key when supported, preferably OCID
- partition metadata in parameters
- retrieval timestamp
- content type
- SHA-256
- byte size
- reproducible relationship to the originating artifact

### FR-11 — Reuse SPEC-004 repository

Persist through the existing `RawEvidenceRepository`.

Do not duplicate INSERT SQL or create a SERCOP-specific raw evidence repository.

### FR-12 — Ingestion summary

Return an immutable summary equivalent to:

```python
@dataclass(frozen=True, slots=True)
class SercopBulkIngestionSummary:
    partition: SercopBulkPartition
    artifact_sha256: str
    artifact_byte_size: int
    source_units_seen: int
    persisted: int
    failed: int
```

### FR-13 — Failure semantics

Differentiate partition/artifact not found, transport failure, invalid artifact, malformed JSON, and individual record failure.

Default preference: fail the partition on one bad record unless `/plan` justifies partial success.

### FR-14 — Transaction behavior

The `/plan` must choose and justify one of:

- whole partition transaction
- per-record transaction
- bounded batch transaction

Do not introduce checkpoint infrastructure.

### FR-15 — Re-running a partition

Duplicate observations may be persisted. No semantic deduplication is required.

### FR-16 — Manual invocation

Provide one simple developer-facing command to ingest exactly one partition, preferably with standard-library argparse.

Example:

```bash
uv run python -m public_intelligence.pipelines.sercop_bulk   --year 2025   --month 1   --type direct_purchase
```

### FR-17 — No automatic backfill

Do not implement loops over all years/months/types.

## 8. Suggested package shape

```text
src/public_intelligence/
├── connectors/
│   └── sercop/
│       └── bulk.py
└── pipelines/
    └── sercop_bulk/
        ├── __init__.py
        ├── models.py
        ├── pipeline.py
        └── __main__.py
```

Avoid generic pipeline/base abstractions.

## 9. Persistence evolution question

SPEC-004 does not have an artifact foreign key.

The `/plan` must decide between:

- no schema change, provenance encoded structurally;
- minimal source-neutral artifact table;
- another minimal representation.

Default preference: avoid schema change if provenance remains unambiguous.

## 10. Testing strategy

- No live SERCOP calls in default tests.
- Use SPEC-002 bulk fixtures or bounded derived fixtures.
- Use real disposable PostgreSQL from SPEC-004.
- Test successful end-to-end fixture ingestion.
- Test artifact and record provenance.
- Test deterministic record bytes/hash.
- Test multiple source units.
- Test malformed/missing artifact and persistence failures.
- Test duplicate rerun behavior.
- Ensure all existing tests continue to pass.

## 11. Acceptance criteria

### Partition model

- [x] SERCOP-specific bulk partition exists.
- [x] Month validation is explicit.
- [x] Procurement type must be nonblank.
- [x] No generic partition framework is introduced.

### Bulk source access

- [x] One official SERCOP bulk partition can be resolved.
- [x] JSON is the only production format.
- [x] HTTP access is async.
- [x] User-Agent and timeout are explicit.
- [x] No aggressive retries or concurrent partition fan-out.

### Artifact provenance

- [x] UTC retrieval timestamp is preserved.
- [x] Requested partition is preserved.
- [x] Artifact URL/path, status, content type, filename, ETag/Last-Modified are preserved where available.
- [x] Artifact SHA-256 and byte size are computed.

### Parsing

- [x] Parser represents only observed supported bulk structure.
- [x] Unknown additive fields are tolerated where safe.
- [x] Invalid minimum envelope fails clearly.
- [x] Ingestion unit is documented.
- [x] Record serialization is deterministic if required.

### Raw persistence

- [x] Existing `RawEvidenceRepository` is reused.
- [x] No duplicate INSERT implementation exists.
- [x] Persisted evidence remains source-neutral.
- [x] OCID is source_key only where supported.
- [x] Partition metadata and artifact relationship are reproducible.
- [x] Duplicate observations remain allowed unless explicitly changed by approved plan.

### Pipeline

- [x] One explicit partition can be ingested end-to-end.
- [x] Immutable summary is returned.
- [x] Seen/persisted/failed counts are accurate.
- [x] Failure and transaction behavior are explicit and tested.
- [x] No automatic backfill exists.

### Manual execution

- [x] One partition can be invoked manually.
- [x] No unnecessary CLI framework is added.
- [x] README documents prerequisites and command.

### Tests

- [x] Default tests make no live SERCOP calls.
- [x] End-to-end test uses real disposable PostgreSQL.
- [x] Successful fixture ingestion, multiple records, provenance, deterministic bytes, failures, and duplicate reruns are tested.
- [x] Existing tests pass.

### Scope

- [x] No procurement domain/entity resolution/events/signals are introduced.
- [x] No scheduler, worker, queue, API/UI, generic ingestion framework, or CSV/XLSX production path is introduced.

### Quality

- [x] lockfile consistent.
- [x] Ruff format/lint pass.
- [x] mypy passes.
- [x] pytest passes.
- [x] migration checks still pass.
- [x] git diff --check passes.

## 12. Definition of Done

SPEC-005 is complete when one supported SERCOP bulk partition can be resolved, downloaded, traced, parsed into source units, persisted as source-neutral raw evidence, and summarized—without entering the procurement domain.

## 13. Suggested `/plan` prompt

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
- src/public_intelligence/connectors/sercop/
- src/public_intelligence/persistence/
- docs/specs/SPEC-005-sercop-historical-bulk-ingestion.md

Plan the implementation of SPEC-005.

Do not modify files yet.

This spec must prove one bounded SERCOP bulk partition end-to-end while
preserving raw evidence and remaining outside the procurement domain.

Your plan must explicitly address:

1. How the official bulk artifact URL is resolved.
2. Exact observed bulk JSON/archive structure.
3. Streaming versus buffered download.
4. Artifact-level provenance.
5. Whether the original artifact is retained.
6. The exact source unit that becomes one RawEvidence row.
7. Deterministic record-byte serialization.
8. Artifact-to-record provenance.
9. Whether SPEC-004 schema changes are required.
10. Transaction boundary.
11. Failure semantics for one malformed record.
12. Duplicate rerun behavior.
13. Manual one-partition CLI design.
14. Real PostgreSQL integration-test strategy.
15. Exact dependencies to add.
16. Exact files expected to create or modify.
17. Any architectural decision requiring an ADR.
18. Overengineering risks.

Do not implement:
- automatic full-history backfill
- scheduler/background workers
- procurement domain entities
- entity resolution
- events
- signals
- API endpoints
- generic ingestion frameworks
- CSV/XLSX production ingestion

Return only the implementation plan.
```

## 14. Human review questions

- Is the ingestion unit based on evidence or convenience?
- Can every persisted row be traced to the exact artifact?
- Are reserialized bytes clearly distinguished from original artifact bytes?
- Is a new artifact table really necessary?
- Is the transaction strategy safe for observed partition sizes?
- Can a malformed record leave misleading partial ingestion?
- Are we introducing scheduling too early?
- Does the pipeline remain outside the procurement domain?
