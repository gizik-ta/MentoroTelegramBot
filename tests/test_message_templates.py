import asyncio
import json

from infrastructure.database.connection import DatabaseConnection
from infrastructure.database.schema import init_db


def test_database_contains_parameterized_message_template_catalog(tmp_path):
    async def scenario():
        db = DatabaseConnection(str(tmp_path / "templates.db"))
        await db.connect()
        await init_db(db)
        async with db.conn.execute(
            """
            SELECT template_key, category, parameters_json
            FROM message_templates
            ORDER BY template_key
            """
        ) as cursor:
            rows = [dict(row) for row in await cursor.fetchall()]
        await db.disconnect()
        return rows

    rows = asyncio.run(scenario())
    categories = {row["category"] for row in rows}

    assert len(rows) >= 14
    assert {"error", "notification", "ad", "admin", "system"} <= categories
    assert all(isinstance(json.loads(row["parameters_json"]), list) for row in rows)
    assert any(
        row["template_key"] == "notification.publication_expiring" for row in rows
    )
