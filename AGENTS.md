# AGENTS.md

## Project

Public Intelligence is an extensible platform for transforming fragmented public information into structured, searchable, and actionable business intelligence.

The project starts with Ecuadorian public data sources, but the architecture must remain source-agnostic.

SERCOP is the first planned data source. It is not the core domain of the system.

## Product language

The core concepts are:

- **Source**: an external public information source.
- **Entity**: a real-world organization, company, institution, product, or other identifiable subject.
- **Event**: a factual occurrence observed from a source.
- **Opportunity**: a potentially actionable situation derived from one or more facts or events.
- **Signal**: an interpretation derived from events, history, rules, or analytics.

Keep the distinction between facts and interpretations explicit.

## Read before coding

Before making architectural changes, read:

- `docs/vision.md`
- relevant files under `docs/adr/`

Before implementing a feature:

1. Read this file.
2. Read the relevant spec under `docs/specs/`.
3. Read any ADR referenced by that spec.
4. Inspect existing code before proposing or implementing changes.

Do not implement a feature based only on a user prompt when a spec exists for it.

## Architecture principles

- Start as a modular monolith.
- Prefer simple designs over distributed systems.
- Keep the domain independent from frameworks and external providers.
- External data sources must be isolated behind connectors/adapters.
- Source-specific schemas must not leak into the core domain.
- Preserve raw source data when practical so it can be reprocessed later.
- Separate ingestion, normalization, domain modeling, and intelligence concerns.
- Prefer explicit data flows over hidden magic.
- Avoid premature abstractions.
- Avoid microservices unless a new ADR explicitly justifies them.
- Avoid infrastructure that is not required by the current milestone.

## Domain rules

The domain should describe business concepts, not vendor/source payloads.

Bad:

```python
release["tender"]["procurementMethod"]
```

Preferred:

```python
procurement.method
```

Connectors are responsible for translating source-specific representations into internal models.

Facts from external sources and derived interpretations must remain distinguishable.

For example:

- `CONTRACT_AWARDED` is an event.
- `PROCUREMENT_ACTIVITY_SPIKE` is a signal.

## Connector rules

Each external data source should have its own connector boundary.

A connector may:

- fetch data
- validate source responses
- handle source pagination
- handle source-specific retries
- expose source DTOs
- translate source failures into internal errors

A connector should not:

- implement business intelligence rules
- directly modify unrelated domain modules
- expose source-specific DTOs as domain entities
- decide whether a business signal is important

## Python guidelines

- Use a supported modern Python version defined by the project.
- Use type hints for public functions and important internal boundaries.
- Prefer small cohesive modules.
- Use descriptive names over clever abstractions.
- Keep domain logic independent from FastAPI, SQLAlchemy, HTTP clients, and other infrastructure libraries.
- Prefer dependency injection at application boundaries.
- Avoid global mutable state.
- Raise meaningful exceptions.
- Do not swallow errors silently.

## Testing

Every implemented behavior should have appropriate tests.

Prefer:

1. unit tests for domain behavior
2. contract/fixture tests for connectors
3. integration tests for persistence and application boundaries where useful
4. a small number of end-to-end tests for critical flows later

Tests must not depend on live public services unless explicitly marked as integration/manual tests.

Use captured fixtures for source response mapping tests when possible.

Do not weaken, skip, or delete valid tests merely to make a change pass.

## Quality checks

Before considering implementation complete, run the project-defined equivalents of:

- formatter
- linter
- type checker
- unit tests

The exact commands belong in the project configuration and README once the foundation is implemented.

## Specs

Specs define implementation scope and observable expectations.

Rules:

- Stay within the current spec.
- Do not silently expand scope.
- Do not add speculative infrastructure for future features.
- Acceptance criteria must be verifiable.
- If implementation reveals a meaningful architectural decision, propose or create an ADR.
- If a spec conflicts with an accepted ADR, stop implementation and report the conflict.
- If requirements are ambiguous but a safe, minimal interpretation exists, use it and document the assumption.

## ADRs

Architectural Decision Records explain important decisions and their consequences.

Create an ADR when a decision:

- changes a major architectural boundary
- introduces an important infrastructure dependency
- affects multiple modules
- is difficult or costly to reverse
- changes an established project principle

Do not create ADRs for routine implementation details.

## Change discipline

- Do not perform unrelated refactors.
- Keep diffs focused.
- Reuse existing patterns before introducing new ones.
- Do not introduce dependencies without a concrete need.
- Prefer deletion and simplification over unnecessary abstractions.
- Update documentation when behavior or architecture changes.

## Security and data ethics

- Treat public data responsibly.
- Respect source terms, legal constraints, rate limits, and access policies.
- Never bypass authentication, access controls, CAPTCHA, or technical restrictions.
- Do not assume that publicly visible information is automatically unrestricted for every form of automated collection or redistribution.
- Do not store secrets in the repository.
- Minimize personal data collection unless it is necessary for a defined use case.

## Definition of Done

A task is complete when:

- the relevant spec acceptance criteria are satisfied
- relevant tests exist and pass
- quality checks pass
- documentation remains accurate
- no unnecessary dependency or infrastructure was introduced
- source-specific concerns remain behind appropriate boundaries
- the implementation is understandable by another developer without relying on chat history

## Working with Codex

For non-trivial work, prefer this loop:

1. Read instructions and relevant documentation.
2. Inspect current code.
3. Produce a short implementation plan.
4. Implement only the agreed scope.
5. Run tests and quality checks.
6. Review the diff against the spec.
7. Report:
   - files changed
   - key decisions
   - tests/checks executed
   - unresolved issues

When asked to review, do not modify code unless the user explicitly asks for fixes.
