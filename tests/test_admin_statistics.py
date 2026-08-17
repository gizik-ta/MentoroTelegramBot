import asyncio
import json
from datetime import datetime, timedelta, timezone

from configuration.config import DEFAULT_ADMIN_ID
from features.admin.rendering import AdminRendering
from features.admin.services import AdminStatisticsServices
from infrastructure.database.connection import DatabaseConnection
from infrastructure.database.repositories.statistics_repo import (
    AdminStatisticsRepository,
)
from infrastructure.database.schema import init_db


def _log_action(user_id: int, timestamp: datetime, elapsed: float, status="success"):
    return {
        "timestamp_utc": timestamp.isoformat(),
        "user_id": user_id,
        "chat_id": user_id,
        "event_type": "Message",
        "handler_name": "sample_handler",
        "processing_time_ms": elapsed,
        "status_code": status,
        "state": "BotFlow:menu_navigation",
    }


def test_admin_statistics_combines_activity_payments_and_ads(tmp_path):
    now = datetime.now(timezone.utc)
    log_path = tmp_path / "actions.jsonl"
    actions = [
        _log_action(101, now - timedelta(days=1), 100),
        _log_action(101, now - timedelta(days=2), 300, "error"),
        _log_action(102, now - timedelta(days=10), 200),
        _log_action(103, now - timedelta(days=40), 400),
        _log_action(DEFAULT_ADMIN_ID, now - timedelta(days=1), 500),
    ]
    log_path.write_text(
        "\n".join(json.dumps(action) for action in actions) + "\n",
        encoding="utf-8",
    )

    async def scenario():
        db = DatabaseConnection(str(tmp_path / "statistics.db"))
        await db.connect()
        await init_db(db)
        await db.conn.executemany(
            "INSERT INTO users (user_id) VALUES (?)",
            [(101,), (102,), (103,)],
        )
        await db.conn.executemany(
            """
            INSERT INTO ads (
                ad_id, user_id, finished, state, is_bought, views, likes
            ) VALUES (?, ?, 1, ?, 1, ?, ?)
            """,
            [
                (1, 101, "published", 5, 2),
                (2, 102, "on_check", 3, 1),
            ],
        )
        paid_transactions = [
            (
                "one",
                101,
                1,
                (now - timedelta(days=10)).isoformat(),
            ),
            (
                "two",
                101,
                1,
                (now - timedelta(days=40)).isoformat(),
            ),
            (
                "three",
                102,
                2,
                (now - timedelta(days=190)).isoformat(),
            ),
        ]
        await db.conn.executemany(
            """
            INSERT INTO transactions (
                uuid, user_id, ad_id, item_id, status,
                created_at, amount_rub, paid_at
            ) VALUES (?, ?, ?, 1, 'paid', ?, 200, ?)
            """,
            [(*row, row[3]) for row in paid_transactions],
        )
        await db.conn.executemany(
            "INSERT INTO user_views (user_id, ad_id) VALUES (?, ?)",
            [(101, 1), (102, 1)],
        )
        await db.conn.commit()

        statistics = await AdminStatisticsServices.get_statistics(
            log_path=log_path,
            now=now,
            repository=AdminStatisticsRepository(db),
        )
        await db.disconnect()
        return statistics

    statistics = asyncio.run(scenario())

    assert statistics.active_users_total == 3
    assert statistics.active_users_30_days == 2
    assert statistics.active_users_7_days == 1
    assert statistics.actions_30_days == 3
    assert statistics.errors_30_days == 1
    assert statistics.average_processing_ms_30_days == 200
    assert statistics.tutors_total == 2
    assert statistics.views_total == 8
    assert statistics.unique_viewers == 2
    assert statistics.paid_orders == 3
    assert statistics.average_purchased_months == 1.5
    assert statistics.revenue_30_days == 200
    assert statistics.revenue_6_months == 400
    assert statistics.revenue_all_time == 600
    assert [item.percentage for item in statistics.subscription_distribution] == [
        50,
        50,
    ]

    rendered = AdminRendering.statistics(statistics)
    assert "За последние 30 дней: 200 ₽" in rendered
    assert "1 мес.: 50.0%" in rendered
    assert "2 мес.: 50.0%" in rendered
