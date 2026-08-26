# Public Intelligence

Public Intelligence is an extensible platform for transforming fragmented
public information into structured, searchable, and actionable business
intelligence.

This repository currently contains the minimal Python application foundation.

## Requirements

- Python 3.13 or newer
- [uv](https://docs.astral.sh/uv/)
- Docker with Docker Compose

## Install dependencies

```bash
uv sync --frozen
```

## Run the API

```bash
uv run uvicorn public_intelligence.api.app:app --reload
```

The health endpoint is available at `http://127.0.0.1:8000/health`.

## Local PostgreSQL

Start the PostgreSQL 18 development service:

```bash
docker compose up -d --wait postgres
```

The committed local-only credentials create the development database at:

```text
postgresql://public_intelligence:public_intelligence@localhost:5432/public_intelligence
```

Apply all migrations explicitly with Yoyo's Psycopg 3 backend:

```bash
uv run yoyo apply --batch \
  --database postgresql+psycopg://public_intelligence:public_intelligence@localhost:5432/public_intelligence
```

Persistence tests use `TEST_DATABASE_URL` only as a maintenance connection from
which they create and drop a uniquely named disposable database. They reject the
development `public_intelligence` database as a maintenance target. The default
matches the local Compose service:

```bash
export TEST_DATABASE_URL=postgresql://public_intelligence:public_intelligence@localhost:5432/postgres
uv run pytest
```

Stop PostgreSQL while retaining its named data volume:

```bash
docker compose down
```

To intentionally delete all local PostgreSQL data, run:

```bash
docker compose down --volumes
```

## Ingest one SERCOP bulk partition

After PostgreSQL is running and migrations have been applied, ingest exactly
one explicitly selected SERCOP JSON partition with:

```bash
DATABASE_URL=postgresql://public_intelligence:public_intelligence@localhost:5432/public_intelligence \
  uv run python -m public_intelligence.pipelines.sercop_bulk \
  --year 2026 \
  --month 7 \
  --type "Obra artística, científica o literaria"
```

Each invocation stores the exact downloaded ZIP response bytes in one
`bulk_partition` raw-evidence row. Each top-level release package is stored in
a separate `bulk_partition_release_package` row using deterministic canonical
JSON derived from the ZIP member. Those package bytes are not the original HTTP
response bytes and are not exact byte slices of the ZIP artifact.

SPEC-005 buffers one explicitly requested artifact as a bounded proof of
capability. The maximum size of real SERCOP partitions is unknown, so this
workflow does not establish production-scale memory behavior. It intentionally
does not schedule partitions, loop over history, retry, checkpoint, or
deduplicate reruns.

## Process one SERCOP partition end to end

With PostgreSQL running and all migrations already applied, preserve raw
evidence and write normalized procurement snapshots for exactly one partition:

```bash
DATABASE_URL=postgresql://public_intelligence:public_intelligence@localhost:5432/public_intelligence \
  uv run python -m public_intelligence.pipelines.procurement \
  --year 2026 \
  --month 7 \
  --type "Obra artística, científica o literaria"
```

A successful command prints one JSON summary containing the ingestion-run ID,
artifact hash and size, source-package count, mapped count, and normalized-save
count. Processing is fail-fast: failures raise instead of returning a partial
success summary. Raw artifact and package evidence remains stored when a later
mapping or normalized-persistence step fails.

## Quality checks

Format the code:

```bash
uv run ruff format .
```

Check formatting without changing files:

```bash
uv run ruff format --check .
```

Run linting:

```bash
uv run ruff check .
```

Run static type checking:

```bash
uv run mypy src tests
```

Run tests:

```bash
uv run pytest
```

Verify that the lockfile matches `pyproject.toml`:

```bash
uv lock --check
```
