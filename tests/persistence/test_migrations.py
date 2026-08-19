from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import psycopg
from psycopg.rows import dict_row
from yoyo import get_backend, read_migrations  # type: ignore[import-untyped]

MIGRATIONS_DIRECTORY = Path(__file__).parents[2] / "migrations"


def _yoyo_url(database_url: str) -> str:
    parsed = urlsplit(database_url)
    return urlunsplit(parsed._replace(scheme="postgresql+psycopg"))


def test_migrations_create_expected_schema_from_empty_database(
    test_database_url: str,
) -> None:
    migrations = read_migrations(str(MIGRATIONS_DIRECTORY))
    with get_backend(_yoyo_url(test_database_url)) as backend:
        assert list(backend.to_apply(migrations)) == []

    with psycopg.connect(test_database_url, row_factory=dict_row) as connection:
        columns = connection.execute(
            """
            SELECT
                column_name,
                data_type,
                udt_name,
                is_nullable,
                column_default
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'raw_evidence'
            ORDER BY ordinal_position
            """
        ).fetchall()
        primary_key = connection.execute(
            """
            SELECT a.attname AS column_name
            FROM pg_index i
            JOIN pg_attribute a
              ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
            WHERE i.indrelid = 'raw_evidence'::regclass AND i.indisprimary
            """
        ).fetchone()

    by_name = {row["column_name"]: row for row in columns}
    assert list(by_name) == [
        "id",
        "source",
        "mechanism",
        "source_key",
        "endpoint",
        "parameters",
        "retrieved_at",
        "http_status",
        "content_type",
        "payload_sha256",
        "payload_byte_size",
        "payload",
        "etag",
        "last_modified",
        "created_at",
    ]
    assert by_name["id"]["udt_name"] == "uuid"
    assert by_name["parameters"]["udt_name"] == "jsonb"
    assert by_name["payload"]["udt_name"] == "bytea"
    assert by_name["retrieved_at"]["data_type"] == "timestamp with time zone"
    assert by_name["created_at"]["data_type"] == "timestamp with time zone"
    assert by_name["source_key"]["is_nullable"] == "YES"
    assert by_name["etag"]["is_nullable"] == "YES"
    assert by_name["last_modified"]["is_nullable"] == "YES"
    assert by_name["created_at"]["column_default"] == "CURRENT_TIMESTAMP"
    assert primary_key == {"column_name": "id"}


def test_migration_files_are_versioned_sql() -> None:
    migration_names = sorted(
        path.name
        for path in Path(MIGRATIONS_DIRECTORY).glob("*.sql")
        if not path.name.endswith(".rollback.sql")
    )
    assert migration_names == ["0001_create_raw_evidence.sql"]
