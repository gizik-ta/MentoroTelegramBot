from .base import BaseRepository


class UserRepository(BaseRepository):
    async def add_user(self, user_id: int) -> None:
        await self.db.conn.execute(
            """
            INSERT OR IGNORE INTO users (user_id)
            VALUES (?)
            """,
            (user_id,),
        )
        await self.db.conn.commit()

    async def get_ui_message_ids(
        self,
        user_id: int,
    ) -> tuple[int | None, int | None]:
        async with self.db.conn.execute(
            """
            SELECT title_message_id, greeting_message_id
            FROM users
            WHERE user_id = ?
            """,
            (user_id,),
        ) as cursor:
            row = await cursor.fetchone()
        if row is None:
            return None, None
        return row["title_message_id"], row["greeting_message_id"]

    async def save_ui_message_ids(
        self,
        user_id: int,
        title_message_id: int | None,
        greeting_message_id: int | None,
    ) -> None:
        await self.db.conn.execute(
            """
            UPDATE users
            SET title_message_id = COALESCE(?, title_message_id),
                greeting_message_id = COALESCE(?, greeting_message_id)
            WHERE user_id = ?
            """,
            (title_message_id, greeting_message_id, user_id),
        )
        await self.db.conn.commit()

    async def get_liked_ad_ids(self, user_id: int) -> list[int]:
        async with self.db.conn.execute(
            "SELECT ad_id FROM user_likes WHERE user_id = ?", (user_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [row["ad_id"] for row in rows]

    async def get_viewed_ad_ids(self, user_id: int) -> list[int]:
        async with self.db.conn.execute(
            "SELECT ad_id FROM user_views WHERE user_id = ?", (user_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [row["ad_id"] for row in rows]
