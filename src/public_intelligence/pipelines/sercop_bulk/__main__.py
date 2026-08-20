"""Command-line entry point for one explicit SERCOP bulk partition."""

import argparse
import asyncio
import json
import os
from collections.abc import Sequence

from public_intelligence.connectors.sercop import SercopBulkClient, SercopBulkPartition
from public_intelligence.persistence import PostgresDatabase, RawEvidenceRepository

from .models import SercopBulkIngestionSummary
from .pipeline import ingest_partition


def build_parser() -> argparse.ArgumentParser:
    """Build the standard-library parser for one explicit partition."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--month", type=int, required=True)
    parser.add_argument("--type", dest="procurement_type", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Validate CLI input, run one partition, and print its summary as JSON."""
    parser = build_parser()
    arguments = parser.parse_args(argv)
    database_url = os.environ.get("DATABASE_URL")
    if database_url is None or not database_url.strip():
        parser.error("DATABASE_URL must contain the migrated PostgreSQL URL")

    try:
        partition = SercopBulkPartition(
            year=arguments.year,
            month=arguments.month,
            procurement_type=arguments.procurement_type,
        )
    except (TypeError, ValueError) as error:
        parser.error(str(error))

    summary = asyncio.run(_run(partition, database_url))
    print(
        json.dumps(
            {
                "year": summary.partition.year,
                "month": summary.partition.month,
                "procurement_type": summary.partition.procurement_type,
                "artifact_sha256": summary.artifact_sha256,
                "artifact_byte_size": summary.artifact_byte_size,
                "source_units_seen": summary.source_units_seen,
                "persisted": summary.persisted,
                "failed": summary.failed,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


async def _run(
    partition: SercopBulkPartition,
    database_url: str,
) -> SercopBulkIngestionSummary:
    async with PostgresDatabase(database_url) as database:
        async with SercopBulkClient() as client:
            return await ingest_partition(
                partition,
                client=client,
                repository=RawEvidenceRepository(database),
            )


if __name__ == "__main__":  # pragma: no cover - exercised through main()
    raise SystemExit(main())
