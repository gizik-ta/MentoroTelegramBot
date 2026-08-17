import aiosqlite


class DatabaseConnection:
    def __init__(self, db_name: str = "app.db"):
        self.db_name = db_name
        self._conn: aiosqlite.Connection | None = None

    async def connect(self):
        """Initialize and open a single shared connection."""
        if self._conn is None:
            self._conn = await aiosqlite.connect(self.db_name)
            self._conn.row_factory = aiosqlite.Row
            await self._conn.execute("PRAGMA foreign_keys = ON")
            await self._conn.execute("PRAGMA journal_mode=WAL;")
            await self._conn.execute("PRAGMA busy_timeout=20000;")
            await self._conn.commit()

    async def disconnect(self):
        """Gracefully close the database connection and flush WAL logs."""
        if self._conn is not None:
            await self._conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")
            await self._conn.close()
            self._conn = None

    @property
    def conn(self) -> aiosqlite.Connection:
        if self._conn is None:
            raise RuntimeError(
                "Database connection is not initialized. "
                "Call 'await db.connect()' first."
            )
        return self._conn


db_conn = DatabaseConnection()
