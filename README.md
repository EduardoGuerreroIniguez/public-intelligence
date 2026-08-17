# Public Intelligence

Public Intelligence is an extensible platform for transforming fragmented
public information into structured, searchable, and actionable business
intelligence.

This repository currently contains the minimal Python application foundation.

## Requirements

- Python 3.13 or newer
- [uv](https://docs.astral.sh/uv/)

## Install dependencies

```bash
uv sync --frozen
```

## Run the API

```bash
uv run uvicorn public_intelligence.api.app:app --reload
```

The health endpoint is available at `http://127.0.0.1:8000/health`.

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
