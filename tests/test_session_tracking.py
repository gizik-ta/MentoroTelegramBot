import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace

from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Chat, Message, User
from common.middleware.session_tracking import SessionTrackingMiddleware
from common.utils.cleaner import MessageCleaner


class FakeActivityService:
    def __init__(self) -> None:
        self.touches = []

    async def touch(self, bot_id: int, chat_id: int, user_id: int) -> None:
        self.touches.append((bot_id, chat_id, user_id))


def test_unmatched_message_is_persisted_for_later_cleanup():
    async def scenario():
        storage = MemoryStorage()
        state = FSMContext(
            storage=storage,
            key=StorageKey(bot_id=9, chat_id=20, user_id=10),
        )
        message = Message(
            message_id=77,
            date=datetime.now(timezone.utc),
            chat=Chat(id=20, type="private"),
            from_user=User(id=10, is_bot=False, first_name="Test"),
            text="unmatched input",
        )
        activity = FakeActivityService()
        middleware = SessionTrackingMiddleware(activity)

        async def unmatched_handler(event, data):
            return None

        await middleware(
            unmatched_handler,
            message,
            {
                "state": state,
                "event_from_user": message.from_user,
                "event_chat": message.chat,
                "bot": SimpleNamespace(id=9),
            },
        )
        return await state.get_data(), activity.touches

    data, touches = asyncio.run(scenario())

    assert data[MessageCleaner.STORAGE_KEY] == [77]
    assert touches == [(9, 20, 10)]
