from features.notifications.models import Notification

from .base import BaseRepository


class NotificationRepository(BaseRepository):
    def _row_to_notification(self, row) -> Notification:
        return Notification(
            notification_id=row["notification_id"],
            user_id=row["user_id"],
            notification_text=row["notification_text"],
            is_read=bool(row["is_read"]),
        )

    async def get_notifications(self, user_id: int) -> list[Notification]:
        async with self.db.conn.execute(
            "SELECT * FROM notifications WHERE user_id = ?", (user_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [self._row_to_notification(r) for r in rows]

    async def send_notification(self, user_id: int, notification_text: str) -> None:
        await self.db.conn.execute(
            """
            INSERT INTO notifications (user_id, notification_text)
            VALUES (?, ?)
            """,
            (user_id, notification_text),
        )
        await self.db.conn.commit()

    async def mark_as_read(self, notification_id: int) -> None:
        await self.db.conn.execute(
            "UPDATE notifications SET is_read = 1 WHERE notification_id = ?",
            (notification_id,),
        )
        await self.db.conn.commit()

    async def count_unread_messages(self, user_id: int) -> int:
        async with self.db.conn.execute(
            """
            SELECT COUNT(*) AS unread
            FROM notifications
            WHERE user_id = ? AND is_read = 0
            """,
            (user_id,),
        ) as cursor:
            row = await cursor.fetchone()
            return row["unread"] if row else 0

    async def delete_notification(self, notification_id: int, user_id: int) -> bool:
        cursor = await self.db.conn.execute(
            """
            DELETE FROM notifications
            WHERE notification_id = ? AND user_id = ?
            """,
            (notification_id, user_id),
        )
        await self.db.conn.commit()
        return cursor.rowcount > 0
