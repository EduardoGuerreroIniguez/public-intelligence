import json
from typing import Any
from uuid import UUID

import pytest

import public_intelligence.pipelines.procurement.__main__ as cli
from public_intelligence.connectors.sercop import SercopBulkPartition
from public_intelligence.pipelines.procurement import ProcurementProcessingSummary


def test_cli_help_lists_partition_arguments(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as captured:
        cli.main(["--help"])

    output = capsys.readouterr().out
    assert captured.value.code == 0
    assert "--year" in output
    assert "--month" in output
    assert "--type" in output


def test_cli_requires_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(SystemExit) as captured:
        cli.main(["--year", "2026", "--month", "7", "--type", "method"])

    assert captured.value.code == 2


def test_cli_requires_all_partition_arguments() -> None:
    with pytest.raises(SystemExit) as captured:
        cli.main(["--year", "2026", "--month", "7"])

    assert captured.value.code == 2


def test_cli_invokes_one_partition_and_prints_success_summary(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    observed: list[tuple[SercopBulkPartition, str]] = []

    async def fake_run(
        partition: SercopBulkPartition,
        database_url: str,
    ) -> ProcurementProcessingSummary:
        observed.append((partition, database_url))
        return _summary(partition)

    monkeypatch.setenv("DATABASE_URL", "postgresql://local/test")
    monkeypatch.setattr(cli, "_run", fake_run)

    result = cli.main(
        [
            "--year",
            "2026",
            "--month",
            "7",
            "--type",
            "Obra artística, científica o literaria",
        ]
    )

    output = json.loads(capsys.readouterr().out)
    assert result == 0
    assert observed == [
        (
            SercopBulkPartition(
                year=2026,
                month=7,
                procurement_type="Obra artística, científica o literaria",
            ),
            "postgresql://local/test",
        )
    ]
    assert output == {
        "artifact_byte_size": 3119,
        "artifact_sha256": "a" * 64,
        "ingestion_run_id": "12345678-1234-5678-1234-567812345678",
        "mapped": 2,
        "month": 7,
        "normalized_saved": 2,
        "procurement_type": "Obra artística, científica o literaria",
        "raw_packages_persisted": 2,
        "source_units_seen": 2,
        "year": 2026,
    }


@pytest.mark.anyio
@pytest.mark.parametrize("should_fail", [False, True])
async def test_run_closes_http_and_database_on_success_or_failure(
    monkeypatch: pytest.MonkeyPatch,
    should_fail: bool,
) -> None:
    events: list[str] = []

    class FakeDatabase:
        def __init__(self, database_url: str) -> None:
            assert database_url == "postgresql://local/test"

        async def __aenter__(self) -> "FakeDatabase":
            events.append("database-enter")
            return self

        async def __aexit__(self, *args: object) -> None:
            events.append("database-exit")

    class FakeClient:
        async def __aenter__(self) -> "FakeClient":
            events.append("client-enter")
            return self

        async def __aexit__(self, *args: object) -> None:
            events.append("client-exit")

    async def fake_process(
        partition: SercopBulkPartition,
        **dependencies: Any,
    ) -> ProcurementProcessingSummary:
        assert dependencies.keys() == {
            "client",
            "raw_repository",
            "procurement_repository",
        }
        events.append("process")
        if should_fail:
            raise RuntimeError("processing failed")
        return _summary(partition)

    monkeypatch.setattr(cli, "PostgresDatabase", FakeDatabase)
    monkeypatch.setattr(cli, "SercopBulkClient", FakeClient)
    monkeypatch.setattr(cli, "process_partition", fake_process)

    if should_fail:
        with pytest.raises(RuntimeError, match="processing failed"):
            await cli._run(_partition(), "postgresql://local/test")
    else:
        assert await cli._run(_partition(), "postgresql://local/test") == _summary(
            _partition()
        )

    assert events == [
        "database-enter",
        "client-enter",
        "process",
        "client-exit",
        "database-exit",
    ]


def _partition() -> SercopBulkPartition:
    return SercopBulkPartition(year=2026, month=7, procurement_type="method")


def _summary(partition: SercopBulkPartition) -> ProcurementProcessingSummary:
    return ProcurementProcessingSummary(
        partition=partition,
        ingestion_run_id=UUID("12345678-1234-5678-1234-567812345678"),
        artifact_sha256="a" * 64,
        artifact_byte_size=3119,
        source_units_seen=2,
        raw_packages_persisted=2,
        mapped=2,
        normalized_saved=2,
    )
