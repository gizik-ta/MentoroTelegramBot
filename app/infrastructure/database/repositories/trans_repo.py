from .base import BaseRepository


class TransactionRepository(BaseRepository):
    async def make_transaction(
        self,
        uuid: str,
        user_id: int,
        ad_id: int,
        item_id: int,
        created_at: str,
        amount_rub: int = 200,
        order_kind: str = "initial",
    ) -> None:
        await self.db.conn.execute(
            """
            INSERT OR IGNORE INTO transactions (
                uuid, user_id, ad_id, item_id, created_at, amount_rub, order_kind
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (uuid, user_id, ad_id, item_id, created_at, amount_rub, order_kind),
        )
        await self.db.conn.commit()

    async def get_by_uuid(self, uuid: str) -> tuple[int, int, str] | None:
        async with self.db.conn.execute(
            "SELECT user_id, ad_id, order_kind FROM transactions WHERE uuid = ?",
            (uuid,),
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return row["user_id"], row["ad_id"], row["order_kind"]
            return None

    async def mark_paid(self, uuid: str) -> None:
        await self.db.conn.execute(
            """
            UPDATE transactions
            SET status = 'paid',
                paid_at = COALESCE(paid_at, strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
            WHERE uuid = ?
            """,
            (uuid,),
        )
        await self.db.conn.commit()
