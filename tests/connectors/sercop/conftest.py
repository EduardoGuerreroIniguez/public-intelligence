from pathlib import Path

import pytest


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def sample_directory() -> Path:
    return Path(__file__).parents[3] / "docs" / "research" / "sercop" / "samples"


@pytest.fixture
def search_body(sample_directory: Path) -> bytes:
    return (sample_directory / "search-2015-agua-page-1.json").read_bytes()


@pytest.fixture
def record_bodies(sample_directory: Path) -> dict[str, bytes]:
    return {
        path.name: path.read_bytes()
        for path in sorted(sample_directory.glob("record-*.json"))
    }
