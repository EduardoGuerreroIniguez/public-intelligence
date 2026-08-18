# SPEC-003 — SERCOP Targeted Connector

**Status:** Implemented  
**Milestone:** 1 — First Real Intelligence  
**Type:** Implementation  
**Depends on:** SPEC-001, SPEC-002

## Context

SPEC-002 established an evidence-based profile of SERCOP's public procurement open-data source.

The research showed that targeted access should initially use two SERCOP mechanisms:

1. keyword search through `search_ocds`
2. exact process lookup through `record?ocid=...`

The observed search response is source-specific and materially different from the record response. Search summaries therefore must not be modeled as reduced versions of the full record payload.

SPEC-002 also found that the inspected record responses behave as source snapshots and are not sufficient evidence for reconstructing a reliable historical event stream.

This spec introduces the first production SERCOP integration boundary while preserving those constraints.

## Problem

The application currently has no production mechanism for querying SERCOP.

Future procurement intelligence needs a small, reliable, source-specific boundary that can:

- search public contracting processes
- retrieve a process snapshot by OCID
- preserve the original source response and retrieval provenance
- represent the observed SERCOP response shapes without leaking them into the core domain
- expose predictable source-access failures to the application layer

Implementing domain procurement entities, persistence, historical ingestion, or business events at the same time would expand the scope beyond what SPEC-002 evidence currently supports.

## Goal

Implement a minimal SERCOP targeted-access connector that supports:

```text
keyword search
     |
     v
SERCOP search summary DTOs

OCID lookup
     |
     v
SERCOP record snapshot DTOs
```

The connector must be:

- source-specific
- typed
- testable without live network access
- fixture-driven using SPEC-002 evidence
- explicit about source errors
- capable of handing raw response evidence and provenance to a future application/persistence boundary

The connector must not create Public Intelligence domain entities or signals.

## Non-goals

SPEC-003 does **not** implement:

- bulk historical ingestion
- PostgreSQL
- database schemas or migrations
- repositories
- ORM models
- procurement domain entities
- Public Intelligence `Event` mappings
- business signals
- opportunity scoring
- entity resolution
- company intelligence
- API/UI endpoints exposing SERCOP
- scheduled polling
- background workers
- caching
- generic connector framework
- generic HTTP client framework
- retry framework
- message brokers
- AI/LLM functionality
- Docker or cloud infrastructure
- automated live integration tests in the default test suite

Do not introduce these speculatively.

## Source evidence

The implementation must be based on:

- `docs/research/sercop/`
- raw fixtures captured by SPEC-002
- official SERCOP open-data API documentation
- official OCDS documentation only where generic OCDS semantics are needed

When generic OCDS documentation and observed SERCOP behavior differ, the connector contract must represent the observed SERCOP source behavior.

## Proposed module boundary

Preferred initial structure:

```text
src/public_intelligence/connectors/sercop/
├── __init__.py
├── client.py
├── models.py
├── errors.py
└── provenance.py
```

Tests:

```text
tests/connectors/sercop/
├── test_search.py
├── test_record.py
├── test_errors.py
└── test_models.py
```

This is guidance, not a requirement to create files that have no meaningful responsibility.

Do not create:

```text
base_connector.py
connector_factory.py
generic_http_client.py
repositories/
services/
mappers/
```

unless the current spec demonstrates an immediate need.

## Terminology

### Connector

A source-specific infrastructure boundary responsible for communicating with SERCOP and representing SERCOP source responses.

### Search summary

The source-specific response item returned by `search_ocds`.

It is **not** a procurement domain entity.

### Record snapshot

The source payload retrieved using `record?ocid=...`.

It represents the source response observed at retrieval time.

It is **not** assumed to represent complete immutable history.

### Raw evidence

The exact successful HTTP response body captured before semantic transformation.

### Provenance

Metadata required to identify where, when, and how raw evidence was retrieved.

# Functional requirements

## FR-1 — SERCOP client

Provide a production SERCOP client in the SERCOP connector module.

The client must expose a small public interface equivalent to:

```python
async def search(
    *,
    year: int,
    search: str,
    page: int = 1,
    buyer: str | None = None,
    supplier: str | None = None,
) -> SearchResult: ...


async def get_record(
    *,
    ocid: str,
) -> RecordResult: ...
```

Exact names may change if Codex identifies a clearer source-specific design, but capabilities and boundaries must remain equivalent.

The client must not expose FastAPI concepts.

## FR-2 — Configurable source base URL

The connector must not hard-code endpoint URLs throughout the implementation.

Define the public open-data base URL in one source-specific location.

Default:

```text
https://datosabiertos.compraspublicas.gob.ec/PLATAFORMA
```

Tests must be able to substitute an in-process/mock transport without accessing the real service.

Do not introduce a general settings framework for this.

## FR-3 — Keyword search request

Use the official SERCOP targeted-search endpoint:

```text
/api/search_ocds
```

Support the documented request parameters:

- `year`
- `search`
- `page`
- `buyer`
- `supplier`

Only include optional parameters when values are supplied.

The connector should validate obvious caller errors before the request where this is part of the documented source contract.

At minimum:

- `year` must be an integer
- `page` must be greater than or equal to 1
- `search` must not be blank

If the documented three-character search minimum is enforced by the implementation, it must be justified by the official source contract and covered by tests.

Do not infer undocumented client-side validation rules from one server response.

## FR-4 — Search response DTO

Represent the observed `search_ocds` response using source-specific typed DTOs.

The model must reflect the fields and value types documented by SPEC-002 fixtures.

At minimum investigate/include the fields needed to preserve the observed search contract, including the observed distinction between:

- numeric `id`
- `ocid`
- numeric `year`
- numeric `month`
- decimal-string monetary summary fields
- buyer name representation
- supplier name representation
- pagination metadata

Fields that were observed as nullable or inconsistent must not be modeled as unconditionally present.

Do not:

- convert buyer/supplier names into entities
- infer RUC from names
- convert decimal strings into a domain money type
- treat numeric search `id` as process identity
- add currency if the search response does not provide one

### Forward compatibility

Unknown fields in successful SERCOP responses must not cause the entire source DTO parse to fail unless they violate an explicit envelope invariant required by this connector.

The connector should tolerate additive source fields.

## FR-5 — Search pagination

Expose enough pagination metadata for a future caller to request subsequent pages explicitly.

SPEC-003 does not implement automatic traversal of all pages.

Example usage:

```python
page1 = await client.search(year=2026, search="agua", page=1)

if page1.has_next:
    page2 = await client.search(year=2026, search="agua", page=2)
```

The exact API may differ based on the observed SERCOP pagination fields.

Do not create an async iterator or automatic paginator unless the source evidence makes it substantially simpler than explicit page access.

## FR-6 — Record lookup

Use the official SERCOP endpoint:

```text
/api/record
```

with:

```text
ocid=<value>
```

Require a non-blank OCID.

Do not attempt to construct or infer OCIDs.

## FR-7 — Record snapshot DTO

Represent the successful record response using source-specific typed DTOs based on SPEC-002 fixtures.

The DTOs should preserve enough structure for future mapping while avoiding a speculative full OCDS implementation.

Model only the source structures required by:

1. fields consistently needed for source identity/provenance
2. structures exercised by SPEC-002 fixtures
3. likely immediate SPEC-004/SPEC-005 needs supported by current evidence

Expected areas include, where present in fixtures:

```text
package metadata
releases[]
release id
release date
release tags
ocid
language
publisher
license
publicationPolicy
extensions
parties
buyer
tender
awards
contracts
relatedProcesses
```

Nested structures may be partially typed where necessary.

### Important

Do not attempt to reproduce the complete OCDS schema in Python.

The project is implementing a SERCOP connector, not an OCDS standards library.

Unknown/additive fields should remain tolerated.

## FR-8 — Nullable and sparse source data

DTOs must reflect the data-quality findings from SPEC-002.

Fields absent in some fixtures must be nullable/optional where appropriate.

Do not create fake default business values such as:

```python
amount = 0
currency = "USD"
suppliers = []
```

unless an empty list is semantically equivalent to the actual source envelope and supported by the source shape.

Missing source data must remain distinguishable from source-provided values.

## FR-9 — Raw response preservation

Every successful connector operation must make the exact raw response body available to the caller together with the typed source representation.

Conceptual result:

```python
@dataclass(frozen=True)
class SourceResult[T]:
    data: T
    raw_body: bytes
    provenance: SourceProvenance
```

The exact type design is implementation-specific.

The requirement is behavioral:

```text
request
   |
   v
exact raw bytes
   +
typed SERCOP DTO
   +
provenance
```

Do not persist the raw response in SPEC-003.

## FR-10 — Provenance

For each successful request, provide provenance containing at minimum:

- source key: `sercop`
- access mechanism
- endpoint/path
- effective request parameters
- retrieval timestamp in UTC
- HTTP status
- content type
- payload SHA-256
- payload byte size

Where available and useful, also preserve relevant response headers such as:

- `Last-Modified`
- `ETag`

Do not store every HTTP header blindly.

### Hashing

SHA-256 must be computed over the exact raw response bytes exposed by the result.

## FR-11 — Source-specific errors

Define a small SERCOP/source connector error hierarchy.

At minimum distinguish:

### `SercopError`

Base connector error.

### `SercopNotFoundError`

The requested OCID/resource is not found.

### `SercopResponseError`

The server returned a response that cannot be accepted as a successful connector result, such as:

- unexpected HTTP status
- malformed expected JSON
- unexpected successful content type
- structurally invalid required envelope

### `SercopTransportError`

The request could not be completed because of transport/network failure.

Exact names may change, but callers must be able to distinguish not-found, transport, and invalid/unexpected-response failures.

Do not expose raw HTTP-library exceptions as the public connector contract.

## FR-12 — Error response behavior

Use SPEC-002 evidence to handle observed source behavior.

In particular, if the source returns an HTML response for an unknown/nonexistent OCID, the connector must classify that behavior according to the observed HTTP status and source semantics instead of trying to parse it as JSON.

Do not rely solely on content type to determine not-found behavior.

Preserve enough error context for debugging without returning full arbitrary HTML bodies in normal exception messages.

## FR-13 — JSON validation

For successful JSON responses:

1. retain raw bytes
2. validate/parse JSON
3. validate the minimum expected source structure
4. construct typed DTOs
5. construct provenance
6. return the result

A response with HTTP 2xx but malformed JSON must fail as a source response error.

A response with JSON that does not match the minimum expected source envelope must fail as a source response error.

Unknown optional/additive fields must remain tolerated.

## FR-14 — HTTP behavior

Use an async HTTP client compatible with the project's dependency direction.

The production client should:

- use a configurable request timeout
- send an explicit descriptive User-Agent
- follow normal HTTP behavior
- avoid automatic aggressive retries
- avoid concurrency beyond the caller's explicit requests

### Timeout

Provide a modest default timeout in one source-specific location.

Do not implement a generic retry policy in SPEC-003.

A future spec can add source-specific resilience if real operational evidence requires it.

## FR-15 — Resource lifecycle

The SERCOP client must provide an explicit resource-lifecycle mechanism.

Acceptable approaches include:

```python
async with SercopClient(...) as client:
    ...
```

or explicit close semantics.

Do not create and leak a new underlying HTTP connection pool for every request.

Tests must verify supported lifecycle behavior where practical.

# Testing requirements

## TR-1 — No live dependency in default tests

The normal test suite must not call SERCOP over the network.

Use:

- SPEC-002 fixtures
- mocked/in-process HTTP transport
- deterministic timestamps or assertions that do not depend on wall-clock precision

Live exploratory checks, if any, must remain manual and outside the default suite.

## TR-2 — Search contract tests

Using captured SPEC-002 fixtures, test at minimum:

- search response parses successfully
- observed JSON field types are preserved
- numeric search `id` remains distinct from `ocid`
- decimal-string summary values are not silently converted into currency-bearing domain values
- buyer/supplier summary representation matches observed fixtures
- nullable fields remain supported
- additive unknown fields do not break parsing
- pagination metadata is exposed

## TR-3 — Search request tests

Verify generated requests for:

- required `year`
- required `search`
- default `page=1`
- explicit page
- buyer optional filter
- supplier optional filter
- omission of absent optional filters

Verify invalid caller inputs that SPEC-003 explicitly chooses to validate.

## TR-4 — Record contract tests

Using SPEC-002 fixtures, verify:

- record response parses successfully
- `ocid` is preserved
- release metadata is preserved
- multiple release tags are preserved
- absence of `compiledRelease` does not fail parsing
- absence of `versionedRelease` does not fail parsing
- sparse optional lifecycle structures do not fail parsing
- extensions and unknown fields do not break the connector

Do not add fabricated compiled/versioned release behavior unless a minimal synthetic fixture is needed solely to verify forward-compatible optional parsing.

## TR-5 — Raw body tests

Verify that:

```text
SHA-256(result.raw_body)
==
result.provenance.payload_sha256
```

and that byte size is exact.

The typed model must be parsed from the same response whose raw bytes are returned.

## TR-6 — Error tests

Test at minimum:

- unknown OCID / observed not-found shape
- unexpected 5xx response
- malformed JSON
- incorrect successful content type
- structurally invalid expected envelope
- transport exception

Tests should assert connector-level errors, not HTTP-library-specific exceptions.

## TR-7 — HTTP client injection

Tests must be able to substitute the network transport/client cleanly.

Do not solve this with a dependency-injection framework.

Use the HTTP library's normal testing/transport facilities or a small constructor boundary.

# Dependency policy

## Existing dependencies first

Before adding a dependency, inspect the current project dependency graph.

Prefer using an already-declared HTTP capability if it satisfies production async requests and deterministic test transport.

Do not add both `httpx` and `httpx2` merely for convenience.

If a new runtime dependency is required, Codex must justify:

- why existing dependencies are insufficient
- why the proposed dependency is minimal
- whether it changes the SPEC-001 test setup

Any dependency addition belongs to SPEC-003 and must be documented in the implementation report.

# Architecture constraints

- Follow `AGENTS.md`.
- Follow ADR-001.
- SERCOP-specific models remain under `connectors/sercop`.
- The domain layer must not import SERCOP DTOs.
- The connector must not import FastAPI.
- The connector must not persist data.
- The connector must not classify opportunities.
- The connector must not emit Public Intelligence events.
- The connector must not perform entity resolution.
- The connector must not become a generic source framework.
- Raw source data and typed source DTOs must remain distinguishable.
- Source facts must remain distinguishable from future interpretations.

# Security and operational constraints

Use only the official public SERCOP open-data endpoints.

The connector must not:

- access authenticated SOCE endpoints
- bypass access controls
- bypass CAPTCHA
- spoof identities
- implement abusive request rates
- scrape unrelated pages as fallback behavior

The User-Agent should identify the project generically and not impersonate a browser or another service.

# Acceptance criteria

## Client

- [x] A production `SercopClient` or equivalent source-specific client exists.
- [x] The client supports keyword search.
- [x] The client supports explicit page selection.
- [x] The client supports optional buyer filtering.
- [x] The client supports optional supplier filtering.
- [x] The client supports lookup by OCID.
- [x] The SERCOP base URL is configured in one source-specific location.
- [x] The client has explicit resource lifecycle handling.

## DTOs

- [x] Search summaries use a source-specific DTO.
- [x] Record snapshots use a separate source-specific DTO.
- [x] Observed search JSON value types from SPEC-002 are represented correctly.
- [x] Numeric search `id` is not treated as the process identifier.
- [x] `ocid` is preserved.
- [x] Record release metadata is preserved.
- [x] Multiple release tags are preserved.
- [x] Sparse/nullable observed fields are supported.
- [x] Unknown additive fields do not break successful parsing.
- [x] The implementation does not attempt to model the complete OCDS standard.

## Raw evidence and provenance

- [x] Every successful search result includes exact raw response bytes.
- [x] Every successful record result includes exact raw response bytes.
- [x] Provenance records source key.
- [x] Provenance records access mechanism.
- [x] Provenance records endpoint and effective request parameters.
- [x] Provenance records UTC retrieval timestamp.
- [x] Provenance records HTTP status.
- [x] Provenance records content type.
- [x] Provenance records SHA-256 of exact payload bytes.
- [x] Provenance records exact payload byte size.

## Errors

- [x] Not-found behavior maps to a source-specific not-found error.
- [x] Transport failures map to a source-specific transport error.
- [x] Malformed JSON maps to a source-specific response error.
- [x] Unexpected successful content type maps to a source-specific response error.
- [x] Invalid required source envelope maps to a source-specific response error.
- [x] Raw HTTP-library exceptions do not form the public connector contract.

## Tests

- [x] Default tests make no live SERCOP requests.
- [x] Tests use SPEC-002 captured fixtures.
- [x] Search parsing is fixture-tested.
- [x] Record parsing is fixture-tested.
- [x] Request parameter generation is tested.
- [x] Pagination behavior is tested.
- [x] Raw-body SHA-256 is tested.
- [x] Raw-body byte size is tested.
- [x] Error mappings are tested.
- [x] Additive unknown source fields are tolerated in tests.
- [x] Existing SPEC-001 tests still pass.

## Scope

- [x] No PostgreSQL/database code is added.
- [x] No persistence repository is added.
- [x] No bulk ingestion is implemented.
- [x] No procurement domain entities are created.
- [x] No Public Intelligence event mappings are created.
- [x] No signal/opportunity logic is created.
- [x] No entity resolution is created.
- [x] No public FastAPI procurement endpoint is created.
- [x] No generic connector framework is introduced.
- [x] No retry framework is introduced.

## Quality

- [x] `uv sync --frozen` succeeds.
- [x] `uv run python -c "import public_intelligence"` succeeds.
- [x] `uv run ruff format --check .` succeeds.
- [x] `uv run ruff check .` succeeds.
- [x] `uv run mypy src tests` succeeds.
- [x] `uv run pytest` succeeds without live public services.
- [x] `uv lock --check` succeeds.
- [x] `git diff --check` succeeds.

# Definition of Done

SPEC-003 is complete when another application layer can reliably and asynchronously:

```python
search_result = await sercop.search(...)
record_result = await sercop.get_record(ocid=...)
```

and receive:

```text
typed SERCOP source data
+
exact raw response evidence
+
retrieval provenance
```

without knowing the underlying HTTP library and without introducing SERCOP-specific structures into the Public Intelligence domain.

The implementation must be sufficiently fixture-backed that development does not require SERCOP availability.

# Suggested `/plan` prompt

```text
/plan

Read:

- AGENTS.md
- docs/vision.md
- docs/adr/ADR-001-modular-monolith.md
- docs/specs/README.md
- docs/specs/SPEC-001-project-foundation.md
- docs/specs/SPEC-002-sercop-data-source-research.md
- docs/research/sercop/
- docs/specs/SPEC-003-sercop-targeted-connector.md

Plan the implementation of SPEC-003.

Do not modify files yet.

Base the design on the actual SPEC-002 fixtures and research, not on
generic OCDS assumptions.

Your plan must explicitly address:

1. The existing HTTP dependency situation, including httpx2.
2. Proposed SERCOP client public interface.
3. Search DTO shape based on captured fixtures.
4. Record DTO scope based on captured fixtures.
5. Raw-body and provenance result design.
6. Error hierarchy and mapping.
7. Async client lifecycle.
8. Test transport strategy with no live network calls.
9. Exact files expected to change.
10. Any ambiguity or overengineering risk in SPEC-003.

Do not implement:
- persistence
- bulk ingestion
- procurement domain entities
- events
- signals
- API endpoints
- generic connector abstractions
```

# Open questions

## OQ-1 — DTO implementation library

The connector needs typed, validated source DTOs.

Before choosing Pydantic, dataclasses, TypedDict, or another approach, inspect the current dependency graph and the complexity of the captured fixtures.

Because FastAPI already depends on Pydantic transitively, using Pydantic may be reasonable, but relying on a transitive dependency directly is a dependency-management decision.

The implementation plan must recommend whether Pydantic should be declared directly or whether another existing approach is simpler.

Do not decide solely because FastAPI uses Pydantic.

## OQ-2 — HTTPX2 production transport

SPEC-001 currently includes HTTPX2 for application test behavior.

The implementation plan must establish whether HTTPX2 is appropriate and supported for production async HTTP requests in this connector.

Do not add HTTPX in parallel unless evidence shows it is necessary.

## OQ-3 — Record DTO depth

SPEC-002 captured nested source structures.

The connector must preserve useful structure without recreating all OCDS schemas.

The implementation plan should identify the minimum typed depth required for immediate future specs and a strategy for tolerating unknown nested fields.

## OQ-4 — Search monetary values

SPEC-002 observed decimal-string monetary summary values without currency.

SPEC-003 should preserve source semantics.

Do not convert these fields into a domain money object or assume USD.

The implementation plan should recommend whether they remain strings or are represented using a source-level decimal value while preserving absence of currency semantics.

## OQ-5 — Provenance ownership

SPEC-003 needs provenance as a connector result concept.

It is not yet decided whether `SourceProvenance` belongs:

- specifically inside the SERCOP connector, or
- in a small source-neutral infrastructure module because future connectors will require the same concept.

Prefer source-local implementation unless immediate reuse is already demonstrated.

Do not introduce a generic abstraction solely for anticipated future sources.
