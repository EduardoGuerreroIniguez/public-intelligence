import json
import os
from collections.abc import AsyncIterator, Iterator
from io import BytesIO
from pathlib import Path
from typing import cast
from urllib.parse import urlsplit, urlunsplit
from uuid import uuid4
from zipfile import ZIP_DEFLATED, ZipFile

import psycopg
import pytest
from psycopg import errors, sql
from yoyo import get_backend, read_migrations  # type: ignore[import-untyped]

from public_intelligence.persistence import PostgresDatabase, RawEvidenceRepository

PROJECT_ROOT = Path(__file__).parents[1]
MIGRATIONS_DIRECTORY = PROJECT_ROOT / "migrations"
SERCOP_SAMPLE_DIRECTORY = PROJECT_ROOT / "docs" / "research" / "sercop" / "samples"
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


@pytest.fixture
def sample_directory() -> Path:
    return SERCOP_SAMPLE_DIRECTORY


@pytest.fixture
def search_body(sample_directory: Path) -> bytes:
    return (sample_directory / "search-2015-agua-page-1.json").read_bytes()


@pytest.fixture
def record_bodies(sample_directory: Path) -> dict[str, bytes]:
    return {
        path.name: path.read_bytes()
        for path in sorted(sample_directory.glob("record-*.json"))
    }


@pytest.fixture
def bulk_source_packages() -> list[dict[str, object]]:
    paths = [
        SERCOP_SAMPLE_DIRECTORY
        / "record-2015-ocds-5wno2w-CE-20150000092768-23237.json",
        SERCOP_SAMPLE_DIRECTORY / "record-2026-ocds-5wno2w-CE-20260002969199-2455.json",
    ]
    return [cast(dict[str, object], json.loads(path.read_bytes())) for path in paths]


@pytest.fixture
def bulk_zip_body(bulk_source_packages: list[dict[str, object]]) -> bytes:
    json_body = json.dumps(
        bulk_source_packages,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    target = BytesIO()
    with ZipFile(target, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("sercop-bulk.json", json_body)
    return target.getvalue()


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
            await connection.execute(
                """
                TRUNCATE TABLE
                    award_suppliers,
                    procurement_contracts,
                    procurement_awards,
                    procurement_suppliers,
                    procurements,
                    raw_evidence
                """
            )
        yield database
    finally:
        await database.close()


@pytest.fixture
def repository(database: PostgresDatabase) -> RawEvidenceRepository:
    return RawEvidenceRepository(database)
