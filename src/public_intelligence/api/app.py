"""FastAPI application entry point."""

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from public_intelligence.persistence import PostgresDatabase, ProcurementQueries

from .explorer import router as explorer_router

_API_DIRECTORY = Path(__file__).resolve().parent
_STATIC_DIRECTORY = _API_DIRECTORY / "static"


def create_app(database_url: str | None = None) -> FastAPI:
    """Create the Public Intelligence API application."""

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        resolved_database_url = database_url
        if resolved_database_url is None:
            resolved_database_url = os.environ.get("DATABASE_URL")
        if resolved_database_url is None or not resolved_database_url.strip():
            raise RuntimeError("DATABASE_URL must contain the migrated PostgreSQL URL")

        async with PostgresDatabase(resolved_database_url) as database:
            application.state.database = database
            application.state.procurement_queries = ProcurementQueries(database)
            yield

    application = FastAPI(title="Public Intelligence", lifespan=lifespan)
    application.mount(
        "/static",
        StaticFiles(directory=_STATIC_DIRECTORY),
        name="static",
    )
    application.include_router(explorer_router)

    @application.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return application


app = create_app()
