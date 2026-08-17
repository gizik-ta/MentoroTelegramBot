import asyncio
from datetime import date

from features.my_ads.subscription_maintenance import SubscriptionMaintenanceService
from features.my_ads.texts import MyAdsTexts
from infrastructure.database.connection import DatabaseConnection
from infrastructure.database.repositories.subscription_repo import (
    SubscriptionMaintenanceRepository,
)
from infrastructure.database.schema import init_db


def test_daily_subscription_expiration_and_reminder_are_idempotent(tmp_path):
    async def scenario():
        db = DatabaseConnection(str(tmp_path / "subscriptions.db"))
        await db.connect()
        await init_db(db)
        await db.conn.executemany(
            "INSERT INTO users (user_id) VALUES (?)",
            [(10,), (20,), (30,)],
        )
        await db.conn.executemany(
            """
            INSERT INTO ads (
                ad_id, user_id, finished, state, is_bought,
                bought_time, publishing_end
            ) VALUES (?, ?, 1, 'published', 1, '2026-07-01', ?)
            """,
            [
                (1, 10, "2026-08-16"),
                (2, 20, "2026-08-17"),
                (3, 30, "2026-08-18"),
            ],
        )
        await db.conn.commit()

        repository = SubscriptionMaintenanceRepository(db)
        service = SubscriptionMaintenanceService("Asia/Yekaterinburg", repository)
        first = await service.run_once(date(2026, 8, 17))
        second = await service.run_once(date(2026, 8, 17))

        async with db.conn.execute(
            "SELECT state, is_bought, bought_time, publishing_end FROM ads WHERE ad_id = 1"
        ) as cursor:
            expired_ad = dict(await cursor.fetchone())
        async with db.conn.execute(
            "SELECT state, publishing_end FROM ads WHERE ad_id = 2"
        ) as cursor:
            ending_ad = dict(await cursor.fetchone())
        async with db.conn.execute(
            "SELECT notification_text FROM notifications WHERE user_id = 20"
        ) as cursor:
            notifications = [row[0] for row in await cursor.fetchall()]
        async with db.conn.execute(
            "SELECT COUNT(*) FROM publication_reminders WHERE ad_id = 2"
        ) as cursor:
            reminder_count = (await cursor.fetchone())[0]
        await db.disconnect()
        return first, second, expired_ad, ending_ad, notifications, reminder_count

    first, second, expired_ad, ending_ad, notifications, reminder_count = asyncio.run(
        scenario()
    )

    assert first == {"expired": 1, "reminders": 1}
    assert second == {"expired": 0, "reminders": 0}
    assert expired_ad == {
        "state": "payment_waiting",
        "is_bought": 0,
        "bought_time": None,
        "publishing_end": None,
    }
    assert ending_ad == {"state": "published", "publishing_end": "2026-08-17"}
    assert notifications == [MyAdsTexts.PUBLICATION_END_REMINDER]
    assert reminder_count == 1
