import asyncio

from features.common.models import TutorAd
from infrastructure.database.connection import DatabaseConnection
from infrastructure.database.repositories.ad_repo import AdRepository
from infrastructure.database.repositories.admin_repo import AdminRepository
from infrastructure.database.schema import init_db


def test_admin_repository_lists_and_atomically_moderates_ads(tmp_path):
    async def scenario() -> None:
        db = DatabaseConnection(str(tmp_path / "moderation.db"))
        await db.connect()
        await init_db(db)
        await db.conn.execute("INSERT INTO users (user_id) VALUES (?)", (101,))
        await db.conn.commit()

        ad_repository = AdRepository(db)
        admin_repository = AdminRepository(db)
        first_id = await ad_repository.add_ad(
            101,
            TutorAd(finished=True, state="on_check", tutor_photo=[]),
        )
        second_id = await ad_repository.add_ad(
            101,
            TutorAd(finished=True, state="on_check", tutor_photo=[]),
        )

        pending = await admin_repository.get_on_check_ads()
        assert [ad.ad_id for ad in pending] == [first_id, second_id]

        approved = await admin_repository.approve_ad(first_id)
        assert approved is not None
        assert approved.state == "published"
        assert await admin_repository.approve_ad(first_id) is None

        rejected = await admin_repository.reject_ad(second_id)
        assert rejected is not None
        assert rejected.state == "rejected"
        assert await admin_repository.get_on_check_ads() == []

        await db.disconnect()

    asyncio.run(scenario())
