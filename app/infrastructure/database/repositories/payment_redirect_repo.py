from .base import BaseRepository


class PaymentRedirectRepository(BaseRepository):
    async def create(
        self,
        token: str,
        transaction_uuid: str,
        user_id: int,
        destination_url: str,
    ) -> None:
        await self.db.conn.execute(
            """
            INSERT INTO payment_redirects (
                token,
                transaction_uuid,
                user_id,
                destination_url
            ) VALUES (?, ?, ?, ?)
            """,
            (token, transaction_uuid, user_id, destination_url),
        )
        await self.db.conn.commit()

    async def attach_message(
        self,
        token: str,
        user_id: int,
        chat_id: int,
        message_id: int,
    ) -> bool:
        cursor = await self.db.conn.execute(
            """
            UPDATE payment_redirects
            SET chat_id = ?, message_id = ?
            WHERE token = ? AND user_id = ?
            """,
            (chat_id, message_id, token, user_id),
        )
        await self.db.conn.commit()
        return cursor.rowcount == 1

    async def attach_ad_message(
        self,
        token: str,
        user_id: int,
        chat_id: int,
        message_id: int,
    ) -> bool:
        cursor = await self.db.conn.execute(
            """
            UPDATE payment_redirects
            SET ad_chat_id = ?, ad_message_id = ?
            WHERE token = ? AND user_id = ?
            """,
            (chat_id, message_id, token, user_id),
        )
        await self.db.conn.commit()
        return cursor.rowcount == 1
