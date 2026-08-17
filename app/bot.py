import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.redis import DefaultKeyBuilder, RedisStorage
from common.middleware import register_handler_timing, register_session_tracking
from common.services import SessionActivityService
from configuration.config import config
from features.ad_making.handlers import ad_making_router
from features.admin.handlers import admin_router
from features.common.handlers import fallback_router
from features.my_ads.handlers import my_ads_router
from features.my_ads.payment_redirect import PaymentRedirectServer
from features.my_ads.subscription_maintenance import SubscriptionMaintenanceService
from features.notifications.handlers import notifications_router
from features.saved.handlers import saved_ads_router
from features.starting.handlers import starting_router
from features.tutor_searching.handlers import tutor_searching_router
from features.user_menu.handlers import user_menu_router
from infrastructure.database import setup_database, shutdown_database


def create_redis_storage() -> RedisStorage:
    return RedisStorage.from_url(
        config.url_redis,
        connection_kwargs={"decode_responses": True},
        key_builder=DefaultKeyBuilder(prefix="pomogator:fsm", with_bot_id=True),
    )


async def main():
    logging.disable(logging.CRITICAL)
    bot = Bot(token=config.bot_token, default=DefaultBotProperties(parse_mode="HTML"))
    storage = create_redis_storage()
    isolation = storage.create_isolation(lock_kwargs={"timeout": 60})
    activity_service = SessionActivityService(
        redis=storage.redis,
        storage=storage,
        isolation=isolation,
        timeout_seconds=config.afk_timeout,
        check_interval_seconds=config.afk_check_interval,
    )
    subscription_service = SubscriptionMaintenanceService(config.app_timezone)
    payment_redirect_server = PaymentRedirectServer(
        db_path=config.db_path,
        bot_token=config.bot_token,
        host=config.payment_redirect_host,
        port=config.payment_redirect_port,
    )

    dp = Dispatcher(storage=storage, events_isolation=isolation)
    register_session_tracking(dp, activity_service)
    register_handler_timing(dp)

    dp.include_router(starting_router)
    dp.include_router(admin_router)
    dp.include_router(user_menu_router)
    dp.include_router(tutor_searching_router)
    dp.include_router(notifications_router)
    dp.include_router(saved_ads_router)
    dp.include_router(my_ads_router)
    dp.include_router(ad_making_router)
    dp.include_router(fallback_router)

    async def startup() -> None:
        await setup_database()
        await payment_redirect_server.start()
        await activity_service.start(bot)
        await subscription_service.start()

    async def shutdown() -> None:
        await subscription_service.stop()
        await activity_service.stop()
        await payment_redirect_server.stop()
        await shutdown_database()

    dp.startup.register(startup)
    dp.shutdown.register(shutdown)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
