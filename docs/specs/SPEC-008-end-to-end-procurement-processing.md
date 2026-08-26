# SPEC-008 — End-to-End Procurement Processing

**Status:** Implemented  
**Milestone:** 2 — First Usable Product  
**Type:** Implementation  
**Depends on:** SPEC-001 through SPEC-007

## 1. Context

Public Intelligence already contains the core building blocks required to process public procurement data:

```text
SERCOP bulk source
      ↓
SPEC-005
RawEvidence persistence
      ↓
SPEC-006
Procurement domain mapping
      ↓
SPEC-007
Normalized procurement persistence
```

However, these capabilities are still separate. SPEC-008 introduces the orchestration that connects them into one operational vertical slice.

## 2. Problem

Today a developer must conceptually perform:

```text
run bulk ingestion
      ↓
find persisted package evidence
      ↓
decode each payload
      ↓
validate SERCOP DTO
      ↓
map to ProcurementRecord
      ↓
save normalized record
```

manually or through separate components.

We need one bounded command that processes one explicit SERCOP partition all the way from source extraction to normalized PostgreSQL records.

## 3. Goal

Implement one workflow:

```text
SERCOP partition
      ↓
download bulk artifact
      ↓
persist raw evidence
      ↓
map each supported package
      ↓
persist normalized ProcurementRecord
      ↓
return processing summary
```

Conceptually:

```python
summary = await process_partition(
    SercopBulkPartition(
        year=2026,
        month=7,
        procurement_type="...",
    )
)
```

A developer must also be able to execute the complete workflow manually from the command line.

## 4. Product value

After this spec, one command should be capable of producing normalized procurement data that can be queried directly.

Example:

```bash
uv run python -m public_intelligence.pipelines.procurement \
  --year 2026 \
  --month 7 \
  --type "Obra artística, científica o literaria"
```

Conceptual result:

```text
Partition processed successfully

Artifact downloaded:     1
Source packages seen:    3
Raw packages persisted:  3
Mapped procurements:     3
Normalized saved:        3
```

Then:

```sql
SELECT source, external_id, buyer_name, procedure_title
FROM procurements;
```

returns normalized business facts.

## 5. Learning walkthrough

### 5.1 What is orchestration?

Orchestration means coordinating components that already exist.

SPEC-008 must not reimplement HTTP, raw persistence, mapping, or normalized SQL. It should call the existing boundaries in sequence.

### 5.2 Application layer

The workflow belongs to an orchestration/application layer:

```text
"first do A,
 then pass result to B,
 then persist through C"
```

It is not domain, connector, or persistence logic.

### 5.3 Vertical slice

Before:

```text
connector exists
repository exists
mapper exists
```

After:

```text
source
 ↓
processing
 ↓
storage
 ↓
queryable result
```

That is the first complete operational vertical slice.

## 6. Architectural principles

The workflow may depend on:

```text
SercopBulkClient
RawEvidenceRepository
SercopRecordPackage
map_procurement_package
ProcurementRepository
```

It must not duplicate connector code, raw SQL, mapping logic, or domain rules.

## 7. Functional requirements

### FR-1 — One explicit partition

Process exactly one `SercopBulkPartition` per invocation.

No automatic iteration across years/months/types.

### FR-2 — Reuse SPEC-005 ingestion

Reuse the existing SERCOP bulk ingestion capability.

If SPEC-005's public result does not expose enough information for downstream normalization, make the smallest bounded refactor necessary.

Do not duplicate package extraction.

### FR-3 — Raw evidence remains first

Persist raw artifact/package evidence before normalized mapping.

### FR-4 — Normalize package evidence

For each canonical release-package RawEvidence:

```text
RawEvidence.payload
      ↓
SercopRecordPackage.model_validate_json(...)
      ↓
map_procurement_package(...)
```

Pass `RawEvidence.id` as the evidence reference.

Do not map the ZIP artifact itself.

### FR-5 — Persist normalized records

Persist every mapped `ProcurementRecord` through the existing `ProcurementRepository`.

### FR-6 — Reprocessing behavior

If a procurement already exists, reuse SPEC-007 snapshot replacement behavior.

Do not implement pipeline-level deduplication/upsert semantics.

### FR-7 — Processing summary

Return an immutable summary with clear semantics, approximately:

```python
@dataclass(frozen=True, slots=True)
class ProcurementProcessingSummary:
    partition: SercopBulkPartition
    ingestion_run_id: UUID | None
    artifact_sha256: str
    artifact_byte_size: int
    source_units_seen: int
    raw_packages_persisted: int
    mapped: int
    normalized_saved: int
```

Align with actual SPEC-005 result types and avoid ambiguous counters.

The workflow is fail-fast: a successful invocation returns this summary and a
failed invocation raises its original explicit exception. Do not add a failure
counter without a successful-return path where it can be non-zero.

### FR-8 — Failure policy

If raw ingestion succeeds but mapping fails, raw evidence remains stored. Stop
on the first downstream failure and raise it; do not return a partial-success
summary or aggregate failures.

After every package has mapped successfully, validate that each
`(source, external_id)` occurs only once in the current run. A duplicate must
fail explicitly before normalized persistence begins. Do not merge records or
use package order to choose a winner. This check is local to SPEC-008; separate
runs continue to use SPEC-007 snapshot replacement normally.

### FR-9 — No giant transaction

Do not place external HTTP, raw persistence, and normalized persistence inside one giant transaction.

### FR-10 — Evidence relationship

Each normalized procurement must reference the exact canonical package RawEvidence used for mapping.

### FR-11 — Manual CLI

Provide one developer command for the complete workflow using standard-library argument parsing unless an existing boundary makes another option simpler.

### FR-12 — Human-readable output

Print a concise processing summary. JSON is acceptable/preferred if consistent with SPEC-005.

### FR-13 — Database prerequisite

Expect migrations to already be applied. Do not auto-run migrations.

### FR-14 — Component lifecycle

Reuse one SERCOP HTTP client and one PostgreSQL pool per invocation.

### FR-15 — No scheduler

Manual execution only.

## 8. Pipeline result semantics

A successful run should answer:

```text
How much source data did we see?
How much raw evidence did we preserve?
How many procurements mapped?
How many normalized snapshots were saved?
Did anything fail?
```

Prefer explicit names such as `raw_packages_persisted` and `normalized_saved`.

## 9. Optional bounded refactor of SPEC-005

If downstream processing cannot access newly persisted package evidence directly, evaluate the smallest change.

Preferred options:

- enrich internal ingestion result with package RawEvidence objects/IDs;
- keep SPEC-005 CLI summary stable;
- avoid adding a raw-evidence query API solely to rediscover rows just inserted.

Default preference:

```text
return evidence produced by the operation
```

## 10. Testing strategy

- Default tests make no live SERCOP calls.
- End-to-end integration uses disposable real PostgreSQL.
- Test mock ZIP → raw evidence → mapping → normalized PostgreSQL.
- Verify normalized evidence_id points to package RawEvidence, not ZIP artifact.
- Test multiple packages.
- Test re-running same partition.
- Test mapping failure leaves raw evidence.
- Test normalized DB failure leaves raw evidence.
- Test clean lifecycle.
- Test CLI `--help`, required args, successful mocked invocation, and output.
- Existing SPEC-001 through SPEC-007 tests remain green.

## 11. Acceptance criteria

### Orchestration

- [x] One end-to-end procurement processing workflow exists.
- [x] One explicit SERCOP partition is processed per invocation.
- [x] Existing bulk ingestion is reused.
- [x] Existing SERCOP mapper is reused.
- [x] Existing ProcurementRepository is reused.
- [x] No duplicate HTTP/parsing/SQL/mapping implementation exists.

### Raw to normalized

- [x] Raw evidence is persisted before normalization.
- [x] Only canonical release-package evidence is mapped.
- [x] Mapping uses `SercopRecordPackage`.
- [x] Mapping receives the package RawEvidence ID.
- [x] Normalized procurement evidence_id points to package evidence.
- [x] ZIP artifact is never mapped as procurement.
- [x] Duplicate normalized identities within one run fail before normalized persistence.

### Reprocessing

- [x] Re-running a partition preserves new raw observations.
- [x] Normalized procurement identity is not duplicated.
- [x] SPEC-007 snapshot replacement behavior is reused.
- [x] Latest normalized evidence reference is updated correctly.

### Failures

- [x] Raw ingestion failures remain explicit.
- [x] Mapping failure policy is explicit.
- [x] Raw evidence remains stored after downstream mapping failure.
- [x] Normalized DB failures do not remove raw evidence.
- [x] No cross-layer giant transaction is introduced.

### CLI

- [x] One command executes the complete workflow.
- [x] CLI processes exactly one partition.
- [x] Database migrations are not run automatically.
- [x] HTTP/database lifecycle is clean.
- [x] CLI prints a clear processing summary.
- [x] No unnecessary CLI framework is added.

### Tests

- [x] Default tests make no live SERCOP requests.
- [x] End-to-end integration uses real PostgreSQL.
- [x] Successful vertical slice is tested.
- [x] Multiple packages are tested.
- [x] Evidence link is tested.
- [x] Duplicate partition run is tested.
- [x] Mapping failure is tested.
- [x] Normalized persistence failure is tested.
- [x] CLI behavior is tested.
- [x] Existing SPEC-001 through SPEC-007 tests pass.

### Scope

- [x] No automatic full-history backfill.
- [x] No scheduler/background worker.
- [x] No API/UI.
- [x] No signals/events/opportunities.
- [x] No entity resolution.
- [x] No generic pipeline/application framework.
- [x] No new persistence abstraction without immediate need.

### Quality

- [x] No unnecessary dependencies.
- [x] lockfile consistent.
- [x] Ruff format/lint pass.
- [x] mypy passes.
- [x] pytest passes.
- [x] migration validation still passes.
- [x] git diff --check passes.

## 12. Definition of Done

SPEC-008 is complete when one command for one SERCOP partition produces both:

```text
traceable raw evidence
+
normalized queryable procurement snapshots
```

without manually coordinating SPEC-005, SPEC-006, and SPEC-007.

## 13. Next milestone steps

After SPEC-008:

```text
SPEC-009 — Basic Procurement Queries
SPEC-010 — Minimal Intelligence Explorer
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
- docs/specs/SPEC-005-sercop-historical-bulk-ingestion.md
- docs/specs/SPEC-006-procurement-domain-mapping.md
- docs/specs/SPEC-007-normalized-procurement-persistence.md
- src/public_intelligence/connectors/sercop/
- src/public_intelligence/pipelines/
- src/public_intelligence/domain/procurement/
- src/public_intelligence/persistence/
- docs/specs/SPEC-008-end-to-end-procurement-processing.md

Plan SPEC-008. Do not modify files.

Explicitly address:

1. Exact orchestration function and location.
2. How SPEC-005 output exposes package RawEvidence for downstream mapping.
3. Whether SPEC-005 needs a bounded result-type refactor.
4. How to avoid querying newly inserted raw rows unnecessarily.
5. Exact RawEvidence -> SercopRecordPackage -> ProcurementRecord flow.
6. Evidence ID propagation into normalized persistence.
7. Mapping failure policy: stop vs continue.
8. Behavior if normalized persistence fails after raw evidence succeeds.
9. Re-run behavior.
10. Processing summary fields and semantics.
11. CLI module/location and output format.
12. HTTP client and DB pool lifecycle.
13. Real PostgreSQL end-to-end test strategy.
14. Mock SERCOP fixture strategy.
15. Exact files to create/modify.
16. Whether any dependency, migration, or ADR is required.
17. Overengineering risks.

Do not implement:
- full-history backfill
- scheduler/workers
- APIs/UI
- signals/events/opportunities
- entity resolution
- generic pipeline frameworks
- new normalized schema
- analytics/query service

Return only the implementation plan.
```

## 15. Human review questions

- Does SPEC-008 mostly connect existing components rather than rebuild them?
- Are package RawEvidence IDs propagated directly instead of rediscovered?
- Is raw evidence preserved even when normalization fails?
- Is normalized upsert delegated entirely to SPEC-007?
- Does one command now produce useful queryable PostgreSQL data?
- Are we keeping this as one vertical slice instead of adding scheduling/backfill?
