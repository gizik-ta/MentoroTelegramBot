from datetime import datetime

from .base import BaseRepository


class FreeTrialRepository(BaseRepository):
    """Persists and atomically consumes one-time 30-day promo entitlements."""

    async def ensure_entitlement(self, user_id: int, notified_at: datetime) -> bool:
        cursor = await self.db.conn.execute(
            """
            INSERT OR IGNORE INTO free_trial_entitlements (user_id, notified_at)
            VALUES (?, ?)
            """,
            (user_id, notified_at.isoformat()),
        )
        await self.db.conn.commit()
        return cursor.rowcount > 0

    async def claim_and_activate(
        self,
        user_id: int,
        ad_id: int,
        activated_at: datetime,
        expires_at: datetime,
    ) -> bool:
        connection = self.db.conn
        activated_value = activated_at.isoformat()
        expires_value = expires_at.isoformat()

        await connection.execute("BEGIN IMMEDIATE")
        try:
            await connection.execute(
                """
                INSERT OR IGNORE INTO free_trial_entitlements (
                    user_id, notified_at
                ) VALUES (?, ?)
                """,
                (user_id, activated_value),
            )
            entitlement = await connection.execute(
                """
                UPDATE free_trial_entitlements
                SET ad_id = ?, consumed_at = ?, activated_at = ?, expires_at = ?
                WHERE user_id = ? AND consumed_at IS NULL
                """,
                (
                    ad_id,
                    activated_value,
                    activated_value,
                    expires_value,
                    user_id,
                ),
            )
            if entitlement.rowcount != 1:
                await connection.rollback()
                return False

            ad = await connection.execute(
                """
                UPDATE ads
                SET is_bought = TRUE,
                    bought_time = ?,
                    publishing_end = ?,
                    state = 'on_check'
                WHERE user_id = ? AND ad_id = ? AND is_bought = FALSE
                """,
                (activated_value, expires_value, user_id, ad_id),
            )
            if ad.rowcount != 1:
                await connection.rollback()
                return False

            await connection.commit()
            return True
        except Exception:
            await connection.rollback()
            raise
