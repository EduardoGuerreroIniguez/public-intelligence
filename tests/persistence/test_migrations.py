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
        normalized_tables = connection.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_name IN (
                  'procurements',
                  'procurement_suppliers',
                  'procurement_awards',
                  'award_suppliers',
                  'procurement_contracts'
              )
            ORDER BY table_name
            """
        ).fetchall()

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
    assert [row["table_name"] for row in normalized_tables] == [
        "award_suppliers",
        "procurement_awards",
        "procurement_contracts",
        "procurement_suppliers",
        "procurements",
    ]


def test_normalized_procurement_schema_matches_domain_storage(
    test_database_url: str,
) -> None:
    with psycopg.connect(test_database_url, row_factory=dict_row) as connection:
        columns = connection.execute(
            """
            SELECT table_name, column_name, data_type, udt_name, is_nullable
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name IN (
                  'procurements',
                  'procurement_suppliers',
                  'procurement_awards',
                  'award_suppliers',
                  'procurement_contracts'
              )
            ORDER BY table_name, ordinal_position
            """
        ).fetchall()
        primary_keys = connection.execute(
            """
            SELECT
                tc.table_name,
                    array_agg(kcu.column_name ORDER BY kcu.ordinal_position)::text[]
                        AS columns
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
              ON kcu.constraint_schema = tc.constraint_schema
             AND kcu.constraint_name = tc.constraint_name
            WHERE tc.constraint_schema = 'public'
              AND tc.constraint_type = 'PRIMARY KEY'
              AND tc.table_name IN (
                  'procurements',
                  'procurement_suppliers',
                  'procurement_awards',
                  'award_suppliers',
                  'procurement_contracts'
              )
            GROUP BY tc.table_name
            ORDER BY tc.table_name
            """
        ).fetchall()
        foreign_keys = connection.execute(
            """
            SELECT tc.table_name, tc.constraint_name, rc.delete_rule
            FROM information_schema.table_constraints tc
            JOIN information_schema.referential_constraints rc
              ON rc.constraint_schema = tc.constraint_schema
             AND rc.constraint_name = tc.constraint_name
            WHERE tc.constraint_schema = 'public'
              AND tc.constraint_type = 'FOREIGN KEY'
              AND tc.table_name IN (
                  'procurements',
                  'procurement_suppliers',
                  'procurement_awards',
                  'award_suppliers',
                  'procurement_contracts'
              )
            ORDER BY tc.table_name, tc.constraint_name
            """
        ).fetchall()
        unique_columns = connection.execute(
            """
            SELECT array_agg(kcu.column_name ORDER BY kcu.ordinal_position)::text[]
                AS columns
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
              ON kcu.constraint_schema = tc.constraint_schema
             AND kcu.constraint_name = tc.constraint_name
            WHERE tc.constraint_schema = 'public'
              AND tc.table_name = 'procurements'
              AND tc.constraint_type = 'UNIQUE'
            GROUP BY tc.constraint_name
            """
        ).fetchall()

    by_table: dict[str, dict[str, object]] = {}
    for row in columns:
        by_table.setdefault(row["table_name"], {})[row["column_name"]] = row

    assert list(by_table["procurements"]) == [
        "id",
        "source",
        "external_id",
        "evidence_id",
        "buyer_present",
        "buyer_external_id",
        "buyer_name",
        "procedure_external_id",
        "procedure_title",
        "procedure_description",
        "procedure_status",
        "procedure_method",
        "procedure_method_details",
        "procedure_category",
        "procedure_value_amount",
        "procedure_value_currency",
        "suppliers_present",
        "awards_present",
        "contracts_present",
        "created_at",
        "updated_at",
    ]
    assert by_table["procurements"]["id"]["udt_name"] == "uuid"  # type: ignore[index]
    assert by_table["procurements"]["evidence_id"]["is_nullable"] == "YES"  # type: ignore[index]
    for table_name, column_name in [
        ("procurements", "procedure_value_amount"),
        ("procurement_awards", "value_amount"),
        ("procurement_contracts", "value_amount"),
    ]:
        assert by_table[table_name][column_name]["data_type"] == "numeric"  # type: ignore[index]
    for table_name, column_name in [
        ("procurements", "created_at"),
        ("procurements", "updated_at"),
        ("procurement_awards", "award_date"),
        ("procurement_contracts", "date_signed"),
    ]:
        assert by_table[table_name][column_name]["data_type"] == (  # type: ignore[index]
            "timestamp with time zone"
        )

    assert {row["table_name"]: row["columns"] for row in primary_keys} == {
        "award_suppliers": ["procurement_id", "award_ordinal", "ordinal"],
        "procurement_awards": ["procurement_id", "ordinal"],
        "procurement_contracts": ["procurement_id", "ordinal"],
        "procurement_suppliers": ["procurement_id", "ordinal"],
        "procurements": ["id"],
    }
    assert [row["columns"] for row in unique_columns] == [["source", "external_id"]]
    assert {
        (row["table_name"], row["constraint_name"]): row["delete_rule"]
        for row in foreign_keys
    } == {
        (
            "award_suppliers",
            "award_suppliers_procurement_id_award_ordinal_fkey",
        ): "CASCADE",
        ("procurement_awards", "procurement_awards_procurement_id_fkey"): "CASCADE",
        (
            "procurement_contracts",
            "procurement_contracts_procurement_id_fkey",
        ): "CASCADE",
        (
            "procurement_suppliers",
            "procurement_suppliers_procurement_id_fkey",
        ): "CASCADE",
        ("procurements", "procurements_evidence_id_fkey"): "RESTRICT",
    }


def test_normalized_migration_rollback_preserves_raw_evidence(
    test_database_url: str,
) -> None:
    rollback_path = (
        MIGRATIONS_DIRECTORY / "0002_create_normalized_procurement.rollback.sql"
    )
    rollback_sql = rollback_path.read_text()
    with psycopg.connect(test_database_url, row_factory=dict_row) as connection:
        connection.execute(rollback_sql)
        tables = connection.execute(
            """
            SELECT
                to_regclass('public.raw_evidence') AS raw_evidence,
                to_regclass('public.procurements') AS procurements,
                to_regclass('public.procurement_suppliers') AS suppliers,
                to_regclass('public.procurement_awards') AS awards,
                to_regclass('public.award_suppliers') AS award_suppliers,
                to_regclass('public.procurement_contracts') AS contracts
            """
        ).fetchone()
        assert tables == {
            "raw_evidence": "raw_evidence",
            "procurements": None,
            "suppliers": None,
            "awards": None,
            "award_suppliers": None,
            "contracts": None,
        }
        connection.rollback()


def test_migration_files_are_versioned_sql() -> None:
    migration_names = sorted(
        path.name
        for path in Path(MIGRATIONS_DIRECTORY).glob("*.sql")
        if not path.name.endswith(".rollback.sql")
    )
    assert migration_names == [
        "0001_create_raw_evidence.sql",
        "0002_create_normalized_procurement.sql",
    ]
