import os
from collections.abc import AsyncIterator, Iterator
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from uuid import uuid4

import psycopg
import pytest
from psycopg import errors, sql
from yoyo import get_backend, read_migrations  # type: ignore[import-untyped]

from public_intelligence.persistence import PostgresDatabase, RawEvidenceRepository

PROJECT_ROOT = Path(__file__).parents[2]
MIGRATIONS_DIRECTORY = PROJECT_ROOT / "migrations"
DEFAULT_MAINTENANCE_URL = (
    "postgresql://public_intelligence:public_intelligence@localhost:5432/postgres"
)


def _database_url(base_url: str, database_name: str) -> str:
    parsed = urlsplit(base_url)
    if parsed.scheme not in {"postgres", "postgresql"} or not parsed.netloc:
        raise ValueError("TEST_DATABASE_URL must be a PostgreSQL URL")
    return urlunsplit(parsed._replace(path=f"/{database_name}"))


def _yoyo_url(database_url: str) -> str:
    parsed = urlsplit(database_url)
    return urlunsplit(parsed._replace(scheme="postgresql+psycopg"))


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(scope="session")
def test_database_url() -> Iterator[str]:
    maintenance_url = os.environ.get("TEST_DATABASE_URL", DEFAULT_MAINTENANCE_URL)
    maintenance_database = urlsplit(maintenance_url).path.lstrip("/")
    if maintenance_database == "public_intelligence":
        raise ValueError(
            "TEST_DATABASE_URL must point to a maintenance database, not the "
            "development public_intelligence database"
        )

    database_name = f"public_intelligence_test_{uuid4().hex}"
    disposable_url = _database_url(maintenance_url, database_name)

    with psycopg.connect(maintenance_url, autocommit=True) as connection:
        connection.execute(
            sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database_name))
        )

    try:
        migrations = read_migrations(str(MIGRATIONS_DIRECTORY))
        with get_backend(_yoyo_url(disposable_url)) as backend:
            with backend.lock():
                backend.apply_migrations(backend.to_apply(migrations))
        yield disposable_url
    finally:
        with psycopg.connect(maintenance_url, autocommit=True) as connection:
            try:
                connection.execute(
                    sql.SQL("DROP DATABASE {}").format(sql.Identifier(database_name))
                )
            except errors.ObjectInUse:
                connection.execute(
                    sql.SQL("DROP DATABASE {} WITH (FORCE)").format(
                        sql.Identifier(database_name)
                    )
                )


@pytest.fixture
async def database(test_database_url: str) -> AsyncIterator[PostgresDatabase]:
    database = PostgresDatabase(test_database_url)
    await database.open()
    try:
        async with database.connection() as connection:
            await connection.execute("TRUNCATE TABLE raw_evidence")
        yield database
    finally:
        await database.close()


@pytest.fixture
def repository(database: PostgresDatabase) -> RawEvidenceRepository:
    return RawEvidenceRepository(database)
