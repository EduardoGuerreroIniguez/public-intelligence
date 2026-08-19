# ADR-002 — PostgreSQL Raw Evidence Persistence

**Status:** Accepted  
**Date:** 2026-08-19

## Context

Public Intelligence needs to preserve exact source response bytes and retrieval
provenance before normalization or domain modeling begins. This is the first
durable persistence capability in the modular monolith.

The initial persistence boundary needs one source-neutral table and two
operations: save raw evidence and retrieve it by an internal identifier.

## Decision

Use PostgreSQL 18 for raw evidence persistence.

Use Psycopg 3 directly for asynchronous, parameterized database access and
`psycopg_pool.AsyncConnectionPool` for explicitly managed connection pooling.
Do not introduce SQLAlchemy for this initial persistence boundary.

Use Yoyo to apply versioned SQL migrations through Psycopg 3. Migrations are an
explicit operational action and are not run during normal application startup.

Store exact payload bytes as PostgreSQL `BYTEA`, structured request parameters
as `JSONB`, internal identifiers as `UUID`, and timestamps as `TIMESTAMPTZ`.

## Why

Direct Psycopg keeps the current implementation explicit and small. An ORM or
SQL expression layer would add concepts without simplifying one table and two
queries. Yoyo supplies transactional migration ordering and tracking while
allowing the schema to remain plain PostgreSQL SQL.

PostgreSQL provides the required binary, JSON, UUID, and timezone-aware types
without additional persistence services or extensions.

## Consequences

- Persistence code is PostgreSQL-specific but source-neutral.
- Callers must explicitly manage the database pool lifecycle.
- Schema changes require committed Yoyo migrations.
- Runtime queries remain explicit SQL and database errors remain Psycopg errors.
- SQLAlchemy can be reconsidered only if later persistence complexity provides
  a concrete benefit.

## Rejected alternatives

### SQLAlchemy 2 async

Rejected for this spec because it would still require a PostgreSQL driver while
adding engine, metadata, and mapping abstractions not needed by the current
interface.

### Hand-written migration runner

Rejected because implementing migration ordering, locking, and applied-version
tracking locally would duplicate established tooling.

### Alembic

Rejected for this direct-Psycopg boundary because it would introduce SQLAlchemy
primarily for migration machinery. Yoyo supports versioned PostgreSQL SQL using
the selected driver.

### Object or distributed storage

Rejected because the current milestone requires a small local persistence
foundation, not multiple storage systems.
