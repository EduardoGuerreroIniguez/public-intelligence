import pytest
from fastapi import FastAPI
from httpx2 import ASGITransport, AsyncClient

from public_intelligence.api.app import create_app


def test_application_creation_succeeds() -> None:
    application = create_app()

    assert isinstance(application, FastAPI)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_health_returns_ok() -> None:
    transport = ASGITransport(app=create_app())

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
