import asyncio

from infrastructure.database.connection import DatabaseConnection
from infrastructure.database.schema import init_db


def test_schema_removes_legacy_rating_column(tmp_path):
    async def scenario():
        db = DatabaseConnection(str(tmp_path / "legacy-rating.db"))
        await db.connect()
        await init_db(db)
        await db.conn.execute("ALTER TABLE ads ADD COLUMN rate REAL DEFAULT 0")
        await db.conn.commit()

        await init_db(db)
        async with db.conn.execute("PRAGMA table_info(ads)") as cursor:
            columns = [row[1] for row in await cursor.fetchall()]
        await db.disconnect()
        return columns

    assert "rate" not in asyncio.run(scenario())
