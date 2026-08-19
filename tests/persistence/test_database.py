import pytest
from psycopg_pool import PoolClosed

from public_intelligence.persistence import PostgresDatabase


@pytest.mark.anyio
async def test_database_context_reuses_and_closes_pool(
    test_database_url: str,
) -> None:
    database = PostgresDatabase(test_database_url, min_size=1, max_size=1)

    async with database:
        async with database.connection() as connection:
            first_pid = await (
                await connection.execute("SELECT pg_backend_pid() AS pid")
            ).fetchone()
        async with database.connection() as connection:
            second_pid = await (
                await connection.execute("SELECT pg_backend_pid() AS pid")
            ).fetchone()

    assert first_pid is not None
    assert second_pid is not None
    assert first_pid["pid"] == second_pid["pid"]

    with pytest.raises(PoolClosed):
        async with database.connection():
            pass
