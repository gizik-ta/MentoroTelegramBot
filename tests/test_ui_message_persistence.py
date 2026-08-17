import asyncio
from types import SimpleNamespace

from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage
from common.middleware.session_tracking import SessionTrackingMiddleware
from common.utils.cleaner import MessageCleaner
from common.utils.title_manager import TitleManager
from infrastructure.database.connection import DatabaseConnection
from infrastructure.database.repositories.user_repo import UserRepository
from infrastructure.database.schema import init_db


class FakeActivityService:
    async def touch(self, bot_id: int, chat_id: int, user_id: int) -> None:
        return None


def test_ui_message_ids_survive_empty_redis_state(tmp_path):
    async def scenario():
        database = DatabaseConnection(str(tmp_path / "ui-messages.db"))
        await database.connect()
        await init_db(database)
        repository = UserRepository(database)
        await repository.add_user(10)
        await repository.save_ui_message_ids(10, 200, 300)

        state = FSMContext(
            storage=MemoryStorage(),
            key=StorageKey(bot_id=9, chat_id=20, user_id=10),
        )
        middleware = SessionTrackingMiddleware(FakeActivityService(), repository)
        event = SimpleNamespace(from_user=SimpleNamespace(id=10))

        async def handler(_event, data):
            restored = await data["state"].get_data()
            assert restored[TitleManager.STORAGE_KEY] == 200
            assert restored[MessageCleaner.GREETING_STORAGE_KEY] == 300
            await data["state"].update_data(**{TitleManager.STORAGE_KEY: 201})

        await middleware(
            handler,
            event,
            {
                "state": state,
                "event_from_user": event.from_user,
            },
        )
        persisted = await repository.get_ui_message_ids(10)
        await database.disconnect()
        return persisted

    assert asyncio.run(scenario()) == (201, 300)
