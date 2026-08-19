"""Explicit lifecycle for the PostgreSQL connection pool."""

from contextlib import AbstractAsyncContextManager

from psycopg import AsyncConnection
from psycopg.rows import DictRow, dict_row
from psycopg_pool import AsyncConnectionPool


class PostgresDatabase:
    """Own and expose a small asynchronous PostgreSQL connection pool."""

    def __init__(
        self,
        connection_url: str,
        *,
        min_size: int = 1,
        max_size: int = 5,
        timeout_seconds: float = 10.0,
    ) -> None:
        self._timeout_seconds = timeout_seconds
        self._pool = AsyncConnectionPool[AsyncConnection[DictRow]](
            conninfo=connection_url,
            min_size=min_size,
            max_size=max_size,
            timeout=timeout_seconds,
            open=False,
            kwargs={
                "options": "-c timezone=UTC",
                "row_factory": dict_row,
            },
        )

    async def __aenter__(self) -> "PostgresDatabase":
        await self.open()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: object | None,
    ) -> None:
        await self.close()

    async def open(self) -> None:
        """Open the pool and wait until its minimum connections are ready."""
        await self._pool.open(wait=True, timeout=self._timeout_seconds)

    async def close(self) -> None:
        """Close all idle connections and stop accepting new acquisitions."""
        await self._pool.close()

    def connection(
        self,
    ) -> AbstractAsyncContextManager[AsyncConnection[DictRow]]:
        """Acquire a pooled connection for one transaction boundary."""
        return self._pool.connection()
