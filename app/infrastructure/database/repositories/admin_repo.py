from features.common.models import TutorAd

from .ad_repo import AdRepository
from .base import BaseRepository


class AdminRepository(BaseRepository):
    """Database operations owned by the administration feature."""

    async def get_on_check_ads(self) -> list[TutorAd]:
        async with self.db.conn.execute(
            "SELECT * FROM ads WHERE state = 'on_check' ORDER BY ad_id ASC"
        ) as cursor:
            rows = await cursor.fetchall()
            return [AdRepository.row_to_ad(row) for row in rows]

    async def get_on_check_ad(self, ad_id: int) -> TutorAd | None:
        async with self.db.conn.execute(
            "SELECT * FROM ads WHERE ad_id = ? AND state = 'on_check'",
            (ad_id,),
        ) as cursor:
            row = await cursor.fetchone()
            return AdRepository.row_to_ad(row) if row else None

    async def approve_ad(self, ad_id: int) -> TutorAd | None:
        return await self._transition_from_on_check(ad_id, "published")

    async def reject_ad(self, ad_id: int) -> TutorAd | None:
        return await self._transition_from_on_check(ad_id, "rejected")

    async def _transition_from_on_check(
        self,
        ad_id: int,
        target_state: str,
    ) -> TutorAd | None:
        cursor = await self.db.conn.execute(
            """
            UPDATE ads
            SET state = ?
            WHERE ad_id = ? AND state = 'on_check'
            RETURNING *
            """,
            (target_state, ad_id),
        )
        row = await cursor.fetchone()
        await cursor.close()
        await self.db.conn.commit()
        return AdRepository.row_to_ad(row) if row else None
