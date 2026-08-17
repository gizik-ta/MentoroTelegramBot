from .base import BaseRepository


class AdminStatisticsRepository(BaseRepository):
    """Read one coherent set of aggregate product and payment statistics."""

    async def get_snapshot(self) -> dict:
        async with self.db.conn.execute(
            """
            SELECT
                COUNT(*) AS ads_total,
                COUNT(DISTINCT user_id) AS tutors_total,
                COALESCE(SUM(state = 'published'), 0) AS ads_published,
                COALESCE(SUM(state = 'on_check'), 0) AS ads_on_check,
                COALESCE(SUM(state = 'rejected'), 0) AS ads_rejected,
                COALESCE(SUM(views), 0) AS views_total,
                COALESCE(SUM(likes), 0) AS saves_total
            FROM ads
            WHERE finished = 1
            """
        ) as cursor:
            ads = dict(await cursor.fetchone())

        async with self.db.conn.execute(
            """
            SELECT
                COUNT(*) AS paid_orders,
                COUNT(DISTINCT user_id) AS paying_tutors,
                COUNT(DISTINCT ad_id) AS paid_ads,
                COALESCE(SUM(amount_rub), 0) AS revenue_all_time,
                COALESCE(SUM(
                    CASE WHEN datetime(COALESCE(paid_at, created_at))
                              >= datetime('now', '-30 days')
                         THEN amount_rub ELSE 0 END
                ), 0) AS revenue_30_days,
                COALESCE(SUM(
                    CASE WHEN datetime(COALESCE(paid_at, created_at))
                              >= datetime('now', '-6 months')
                         THEN amount_rub ELSE 0 END
                ), 0) AS revenue_6_months,
                COALESCE(SUM(
                    CASE WHEN datetime(COALESCE(paid_at, created_at))
                              >= datetime('now', '-30 days')
                         THEN 1 ELSE 0 END
                ), 0) AS paid_orders_30_days,
                COALESCE(SUM(
                    CASE WHEN datetime(COALESCE(paid_at, created_at))
                              >= datetime('now', '-6 months')
                         THEN 1 ELSE 0 END
                ), 0) AS paid_orders_6_months
            FROM transactions
            WHERE status = 'paid'
            """
        ) as cursor:
            payments = dict(await cursor.fetchone())

        async with self.db.conn.execute(
            """
            SELECT purchased_months, COUNT(*) AS ads_count
            FROM (
                SELECT ad_id, COUNT(*) AS purchased_months
                FROM transactions
                WHERE status = 'paid' AND item_id = 1
                GROUP BY ad_id
            )
            GROUP BY purchased_months
            ORDER BY purchased_months
            """
        ) as cursor:
            subscription_distribution = [dict(row) for row in await cursor.fetchall()]

        async with self.db.conn.execute(
            "SELECT COUNT(DISTINCT user_id) AS unique_viewers FROM user_views"
        ) as cursor:
            unique_viewers = (await cursor.fetchone())["unique_viewers"]

        return {
            **ads,
            **payments,
            "unique_viewers": unique_viewers,
            "subscription_distribution": subscription_distribution,
        }
