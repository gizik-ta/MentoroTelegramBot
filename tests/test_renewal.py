import asyncio
from datetime import datetime, timezone

from features.common.models import TutorAd
from features.common.rendering import render_message
from features.common.texts import CommonTexts
from features.my_ads.keyboards import MyAdsKeyboards
from features.my_ads.rendering import MyAdsRendering
from features.my_ads.texts import MyAdsTexts
from infrastructure.database.connection import DatabaseConnection
from infrastructure.database.repositories.ad_repo import AdRepository
from infrastructure.database.repositories.free_trial_repo import FreeTrialRepository
from infrastructure.database.repositories.trans_repo import TransactionRepository
from infrastructure.database.schema import init_db
from infrastructure.database.services import AdService


def test_published_ad_shows_renewal_and_formatted_end_date():
    ad = TutorAd(
        ad_id=7,
        state="published",
        is_bought=True,
        publishing_end="2026-08-31",
    )

    keyboard = MyAdsKeyboards.process_ads(ad.ad_id, ad.is_bought, ad.state)
    rendered = render_message(
        ad,
        show_state=True,
        show_publication_end=True,
    )
    payment_text, _ = MyAdsRendering.payment("https://example.test", is_renewal=True)

    assert keyboard.inline_keyboard[0][0].text == CommonTexts.RENEW_AD_BUTTON
    assert "ОПУБЛИКОВАНО ДО 31.08.2026" in rendered
    assert MyAdsTexts.RENEWAL_PAYMENT_PURPOSE in payment_text


def test_renewal_payment_extends_existing_published_period(tmp_path):
    async def scenario():
        db = DatabaseConnection(str(tmp_path / "renewal.db"))
        await db.connect()
        await init_db(db)
        await db.conn.execute("INSERT INTO users (user_id) VALUES (10)")
        await db.conn.commit()

        ad_repository = AdRepository(db)
        transaction_repository = TransactionRepository(db)
        ad_id = await ad_repository.add_ad(
            10,
            TutorAd(
                finished=True,
                state="published",
                is_bought=True,
                bought_time="2026-08-01",
                publishing_end="2026-08-31",
            ),
        )
        await transaction_repository.make_transaction(
            "renew-order",
            10,
            ad_id,
            1,
            "2026-08-17T10:00:00+00:00",
            200,
            "renewal",
        )
        service = AdService(
            ad_repository,
            transaction_repository,
            FreeTrialRepository(db),
        )
        await service.activate_ad(
            "renew-order",
            datetime(2026, 8, 17, 10, tzinfo=timezone.utc),
        )

        ad = await ad_repository.get_by_id(ad_id)
        async with db.conn.execute(
            "SELECT status, order_kind FROM transactions WHERE uuid = 'renew-order'"
        ) as cursor:
            transaction = dict(await cursor.fetchone())
        await db.disconnect()
        return ad, transaction

    ad, transaction = asyncio.run(scenario())

    assert ad.state == "published"
    assert ad.is_bought is True
    assert ad.publishing_end == "2026-09-30"
    assert transaction == {"status": "paid", "order_kind": "renewal"}
