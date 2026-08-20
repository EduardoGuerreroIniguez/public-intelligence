import json

import pytest

from public_intelligence.connectors.sercop import SercopBulkPartition
from public_intelligence.pipelines.sercop_bulk import SercopBulkIngestionSummary
from public_intelligence.pipelines.sercop_bulk import __main__ as cli


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


def test_cli_invokes_exactly_one_partition_and_prints_summary(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    observed: list[tuple[SercopBulkPartition, str]] = []

    async def fake_run(
        partition: SercopBulkPartition,
        database_url: str,
    ) -> SercopBulkIngestionSummary:
        observed.append((partition, database_url))
        return SercopBulkIngestionSummary(
            partition=partition,
            artifact_sha256="a" * 64,
            artifact_byte_size=3119,
            source_units_seen=3,
            persisted=3,
            failed=0,
        )

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
    assert len(observed) == 1
    assert observed[0][0] == SercopBulkPartition(
        year=2026,
        month=7,
        procurement_type="Obra artística, científica o literaria",
    )
    assert observed[0][1] == "postgresql://local/test"
    assert output["artifact_byte_size"] == 3119
    assert output["persisted"] == 3
