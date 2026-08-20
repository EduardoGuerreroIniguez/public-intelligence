import pytest


@pytest.fixture
def bulk_response_headers() -> dict[str, str]:
    return {
        "content-type": "application/zip",
        "content-disposition": 'attachment; filename="sercop-partition.zip"',
        "etag": '"bulk-etag"',
        "last-modified": "Sun, 16 Aug 2026 20:35:45 GMT",
    }
