from datetime import date

import aiosqlite

from .base import BaseRepository


class SubscriptionMaintenanceRepository(BaseRepository):
    async def process_day(
        self, current_date: date, reminder_text: str
    ) -> dict[str, int]:
        date_value = current_date.isoformat()
        try:
            await self.db.conn.execute("BEGIN IMMEDIATE")
            expired = await self.db.conn.execute(
                """
                UPDATE ads
                SET publishing_end = NULL,
                    bought_time = NULL,
                    is_bought = 0,
                    state = 'payment_waiting'
                WHERE state = 'published'
                  AND publishing_end IS NOT NULL
                  AND date(publishing_end) < date(?)
                """,
                (date_value,),
            )
            expired_count = expired.rowcount

            async with self.db.conn.execute(
                """
                SELECT ad_id, user_id
                FROM ads
                WHERE state = 'published'
                  AND publishing_end IS NOT NULL
                  AND date(publishing_end) = date(?)
                """,
                (date_value,),
            ) as cursor:
                ending_ads = await cursor.fetchall()

            reminder_count = 0
            for ad in ending_ads:
                reminder = await self.db.conn.execute(
                    """
                    INSERT OR IGNORE INTO publication_reminders (
                        ad_id, reminder_date
                    ) VALUES (?, ?)
                    """,
                    (ad["ad_id"], date_value),
                )
                if reminder.rowcount == 0:
                    continue
                await self.db.conn.execute(
                    """
                    INSERT INTO notifications (user_id, notification_text)
                    VALUES (?, ?)
                    """,
                    (ad["user_id"], reminder_text),
                )
                reminder_count += 1

            await self.db.conn.commit()
            return {"expired": expired_count, "reminders": reminder_count}
        except aiosqlite.Error:
            await self.db.conn.rollback()
            raise
