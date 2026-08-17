import asyncio

from features.common.models import TutorAd
from infrastructure.database.connection import DatabaseConnection
from infrastructure.database.repositories.ad_repo import AdRepository
from infrastructure.database.schema import init_db


def test_every_display_increments_views_but_unique_viewer_stays_unique(tmp_path):
    async def scenario():
        db = DatabaseConnection(str(tmp_path / "views.db"))
        await db.connect()
        await init_db(db)
        await db.conn.executemany(
            "INSERT INTO users (user_id) VALUES (?)",
            [(10,), (20,)],
        )
        await db.conn.commit()

        repository = AdRepository(db)
        ad_id = await repository.add_ad(
            10,
            TutorAd(finished=True, state="published", is_bought=True),
        )

        await repository.view_ad(ad_id, 20)
        await repository.view_ad(ad_id, 20)

        ad = await repository.get_by_id(ad_id)
        async with db.conn.execute(
            "SELECT COUNT(*) FROM user_views WHERE ad_id = ?",
            (ad_id,),
        ) as cursor:
            unique_view_rows = (await cursor.fetchone())[0]
        await db.disconnect()
        return ad.views, unique_view_rows

    views, unique_view_rows = asyncio.run(scenario())

    assert views == 2
    assert unique_view_rows == 1
