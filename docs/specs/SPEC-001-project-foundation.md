# SPEC-001 — Project Foundation

**Status:** Draft  
**Milestone:** 0 — Build the Harness

## Context

Public Intelligence currently has a product vision and architectural direction but no executable project foundation.

Before implementing public-data connectors or business logic, the repository needs a minimal, reliable Python development environment that supports spec-driven, AI-assisted development.

This spec intentionally creates infrastructure only for immediate development needs.

## Problem

Without a consistent project foundation:

- Codex may introduce inconsistent tooling
- development commands may vary between tasks
- tests may be added inconsistently
- source modules may grow without a clear package structure
- quality checks may become difficult to reproduce
- future specs may need to repeatedly solve foundational concerns

## Goal

Create a small executable Python project that:

- has a clear package layout
- can run a minimal FastAPI application
- exposes a health endpoint
- has automated formatting/linting/type checking
- has automated tests
- can run locally with simple documented commands
- establishes the module boundaries needed for future work

After this spec, the repository should be ready for the first real data-source spec.

## Non-goals

This spec does **not** implement:

- SERCOP integration
- any external HTTP data source
- PostgreSQL
- database migrations
- business entities beyond placeholders required for package structure
- procurement logic
- event persistence
- signals
- authentication
- users
- authorization
- frontend
- AI/LLM integration
- background workers
- message brokers
- cloud infrastructure
- CI/CD pipelines unless added through a later spec
- production deployment configuration

Do not add these speculatively.

## Functional requirements

### FR-1 — Python package

Create an installable Python package named:

`public_intelligence`

Use a `src/` layout.

Expected root package:

```text
src/public_intelligence/
```

### FR-2 — Application entry point

Provide a minimal FastAPI application.

The application should be creatable/importable without external infrastructure.

Preferred pattern:

```python
create_app()
```

or an equivalently testable application factory.

### FR-3 — Health endpoint

Expose:

```http
GET /health
```

Successful response:

```json
{
  "status": "ok"
}
```

HTTP status:

`200`

The endpoint must not depend on a database or external service.

### FR-4 — Initial module boundaries

Create the package structure required to communicate intended boundaries.

At minimum:

```text
src/public_intelligence/
|-- domain/
|-- connectors/
|-- pipelines/
|-- intelligence/
|-- persistence/
`-- config/
```

Empty packages are acceptable where no behavior is currently required.

Do not invent abstractions merely to populate them.

### FR-5 — Tests

Configure pytest.

At minimum provide tests verifying:

- application creation succeeds
- `GET /health` returns HTTP 200
- response matches the documented health payload

Tests must run without network access.

### FR-6 — Formatting and linting

Configure Ruff for formatting and linting.

The configuration should live in `pyproject.toml` unless there is a strong technical reason otherwise.

### FR-7 — Type checking

Configure a Python static type checker.

Preferred default: mypy.

Do not pursue excessively strict configuration in this first spec.

The goal is useful type safety without creating unnecessary friction.

### FR-8 — Dependency management

Use `pyproject.toml` as the primary project metadata and dependency configuration.

Keep runtime dependencies minimal.

Expected runtime dependencies should initially be limited to what the minimal API needs.

Development dependencies may include:

- pytest
- HTTP test client dependency if needed
- Ruff
- mypy

Do not add libraries for anticipated future work.

### FR-9 — Local developer commands

Document simple commands for:

- installing dependencies
- running the API
- formatting
- linting
- type checking
- running tests

Commands should be reproducible and understandable without chat context.

### FR-10 — Python version

Select one modern supported Python version and document it consistently.

Preferred initial choice:

`Python 3.13`

If implementation identifies a concrete dependency compatibility issue, use Python 3.12 and document the reason.

Do not change the version merely from preference.

## Technical constraints

- Follow `AGENTS.md`.
- Follow ADR-001.
- Keep the system a modular monolith.
- Do not add a database.
- Do not add Docker unless explicitly added to this spec in a later revision.
- Do not add cloud-specific configuration.
- Do not add a dependency-injection framework.
- Do not introduce repository/service abstractions without actual behavior requiring them.
- FastAPI code must not become the location for future domain logic.

## Proposed initial structure

```text
.
|-- AGENTS.md
|-- README.md
|-- pyproject.toml
|-- src/
|   `-- public_intelligence/
|       |-- __init__.py
|       |-- api/
|       |   |-- __init__.py
|       |   `-- app.py
|       |-- domain/
|       |-- connectors/
|       |-- pipelines/
|       |-- intelligence/
|       |-- persistence/
|       `-- config/
|-- tests/
|   `-- test_health.py
`-- docs/
    |-- vision.md
    |-- adr/
    `-- specs/
```

Codex may make minor structural improvements if they are clearly justified and remain within the spec.

## API contract

### `GET /health`

Response:

```json
{
  "status": "ok"
}
```

Status:

`200 OK`

No external dependency health checks are part of this endpoint in SPEC-001.

## Testing strategy

### Unit/application tests

Use FastAPI's supported testing approach.

Verify:

1. application can be instantiated
2. health endpoint exists
3. health endpoint returns 200
4. payload equals `{"status": "ok"}`

No live network services should be required.

## Acceptance criteria

- [ ] `pyproject.toml` exists and defines project metadata.
- [ ] The project uses a `src/` package layout.
- [ ] `public_intelligence` can be imported.
- [ ] A minimal FastAPI app exists.
- [ ] `GET /health` returns `200`.
- [ ] `GET /health` returns exactly `{"status": "ok"}`.
- [ ] pytest is configured.
- [ ] health endpoint tests pass.
- [ ] Ruff formatting is configured.
- [ ] Ruff linting is configured.
- [ ] static type checking is configured.
- [ ] runtime dependencies remain minimal.
- [ ] no database dependency is introduced.
- [ ] no external data-source integration is introduced.
- [ ] no AI dependency is introduced.
- [ ] README documents local development commands.
- [ ] project structure reflects the modular-monolith boundaries from ADR-001.
- [ ] all documented quality checks pass.

## Suggested Codex implementation workflow

Before editing files:

1. Read `AGENTS.md`.
2. Read `docs/vision.md`.
3. Read `docs/adr/ADR-001-modular-monolith.md`.
4. Read this spec.
5. Inspect the repository.
6. Produce a concise implementation plan.
7. Identify any conflicts or unnecessary proposed dependencies.

Only after reviewing the plan should implementation begin.

## Suggested implementation report

When complete, report:

- files created
- files modified
- dependencies introduced and why
- commands executed
- test results
- lint/type-check results
- deviations from this spec
- unresolved issues

## Open questions

### OQ-1 — Packaging tool

The spec requires `pyproject.toml` but intentionally does not prescribe Poetry, Hatch, PDM, uv, or another higher-level packaging workflow.

Initial preference:

Use the simplest approach that supports reproducible local development.

Do not add tooling solely because it is fashionable.

### OQ-2 — Docker

Docker is intentionally excluded from SPEC-001.

It should be introduced when it solves an actual project need, likely when PostgreSQL or another local infrastructure dependency arrives.

### OQ-3 — CI

CI is intentionally deferred.

Once the first connector exists, a separate small spec can introduce GitHub Actions for repeatable quality checks.
