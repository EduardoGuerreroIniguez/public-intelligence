# ADR-001 — Start as a Modular Monolith

**Status:** Accepted  
**Date:** 2026-08-13

## Context

Public Intelligence is expected to grow across multiple domains and public information sources.

Potential capabilities include:

- source ingestion
- raw data preservation
- normalization
- entity management
- procurement intelligence
- regulatory intelligence
- event history
- signal detection
- analytics
- APIs
- later AI-assisted functionality

Because the conceptual system has multiple areas, it would be easy to prematurely split it into services such as:

- ingestion-service
- company-service
- procurement-service
- signal-service
- AI-service

The project is currently a hobby/validation project with one developer and AI-assisted development through Codex.

Its primary engineering need is fast iteration with clear boundaries, not independent deployment or distributed scaling.

## Decision

The project will start as a **modular monolith**.

The application will be deployed and developed as a single system while maintaining explicit internal module boundaries.

Initial logical modules may include:

- domain
- connectors
- pipelines
- intelligence
- persistence
- API/application layer

Modules must communicate through explicit interfaces and domain models rather than reaching into each other's implementation details.

External source schemas must remain isolated in their connector modules.

## Proposed shape

```text
src/public_intelligence/
|
|-- domain/
|   |-- companies/
|   |-- procurement/
|   |-- events/
|   `-- signals/
|
|-- connectors/
|   `-- sercop/
|
|-- pipelines/
|
|-- intelligence/
|   `-- rules/
|
|-- persistence/
|
`-- config/
```

This structure may evolve through future specs and ADRs.

## Why

A modular monolith provides:

- low operational complexity
- easy local development
- simpler debugging
- simple integration testing
- straightforward database transactions
- easier refactoring while the domain is still being discovered
- less infrastructure to maintain
- better context for AI coding agents
- fast iteration for a small project

At the same time, internal modular boundaries help prevent the codebase from becoming an unstructured monolith.

## Alternatives considered

### Microservices from the beginning

Rejected.

There is currently no demonstrated requirement for:

- independent deployment
- independent scaling
- separate teams
- fault isolation between services
- different technology stacks

Microservices would introduce:

- networking
- distributed tracing
- deployment complexity
- contract management
- eventual consistency
- additional local development overhead

without solving a current project problem.

### Single unstructured application

Rejected.

A completely flat application might optimize the first few days of development but would encourage coupling between:

- external APIs
- domain logic
- persistence
- FastAPI
- intelligence logic

This would make future source integration and refactoring harder.

### Event-driven distributed architecture

Rejected for the initial stage.

Events are important as a **domain concept**, but this does not imply the need for Kafka, a message broker, or distributed event-driven infrastructure.

Domain events and historical events can initially exist inside the modular monolith and persistence layer.

## Consequences

### Positive

- simple deployment
- rapid development
- easier testing
- easier Codex-assisted changes
- architectural boundaries remain visible
- future extraction remains possible if a real need emerges

### Negative

- modules share a deployment lifecycle
- a single application can eventually become large
- discipline is required to prevent cross-module coupling
- scaling is initially application-wide

These costs are acceptable at the current project stage.

## Rules resulting from this ADR

1. New functionality should normally be added as a module inside the monolith.
2. A new external source should normally be implemented as a connector.
3. Modules should not import infrastructure-specific details from unrelated modules.
4. The domain must remain independent from FastAPI and source clients.
5. Adding a message broker requires a separate ADR.
6. Extracting a microservice requires a separate ADR with a demonstrated operational or organizational need.
7. "We may need it later" is not sufficient justification for a distributed component.

## Revisit conditions

Reconsider this ADR when one or more of the following become true:

- a module requires materially different scaling characteristics
- independent deployments become necessary
- multiple teams require ownership boundaries
- reliability requirements require process isolation
- deployment frequency differs significantly between modules
- a component needs a substantially different technology stack
- the modular monolith is creating a measured delivery or operational bottleneck

Until then, modular monolith remains the default architecture.
