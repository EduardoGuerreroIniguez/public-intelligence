# Specs

Specs define bounded units of implementation work.

A spec should normally be small enough to implement and review as one focused change.

## Status values

Recommended statuses:

- Draft
- Accepted
- In Progress
- Implemented
- Superseded

## Naming

Use:

```text
SPEC-NNN-short-description.md
```

Example:

```text
SPEC-003-sercop-ingestion.md
```

## Template

```md
# SPEC-XXX — Feature name

**Status:** Draft
**Milestone:** X

## Context

Why does this capability exist?

## Problem

What concrete problem are we solving?

## Goal

What should exist after implementation?

## Non-goals

What is explicitly outside this work?

## Functional requirements

### FR-1 — Requirement name

Observable behavior.

## Technical constraints

Important implementation boundaries.

## Domain considerations

Relevant entities, events, value objects, or terminology.

## Proposed interfaces

Optional API/classes/events/contracts.

## Testing strategy

Expected tests and important failure cases.

## Acceptance criteria

- [ ] Verifiable result
- [ ] Another verifiable result

## Open questions

Known unresolved questions.
```

## Guidance

Good specs:

- describe behavior and boundaries
- define non-goals
- use verifiable acceptance criteria
- avoid prescribing unnecessary implementation details
- reference accepted ADRs
- remain understandable without chat history

Avoid:

- huge multi-feature specs
- speculative requirements
- architecture changes hidden inside feature specs
- acceptance criteria such as "works correctly"
- requirements that cannot be tested or observed
