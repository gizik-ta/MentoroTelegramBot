import asyncio
import time
from contextlib import asynccontextmanager
from types import SimpleNamespace

import fakeredis.aioredis
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.redis import DefaultKeyBuilder, RedisStorage
from common.services import session_activity as session_module
from common.services.session_activity import SessionActivityService
from common.utils.cleaner import MessageCleaner
from common.utils.title_manager import TitleManager
from features.common.states import BotFlow, CardMaking


class FakeBot:
    id = 9

    def __init__(self):
        self.deleted = []
        self.sent = []
        self.next_message_id = 1000

    async def delete_messages(self, chat_id, message_ids):
        self.deleted.extend((chat_id, message_id) for message_id in message_ids)

    async def delete_message(self, chat_id, message_id):
        self.deleted.append((chat_id, message_id))

    async def send_message(self, chat_id, text, reply_markup=None, parse_mode=None):
        message = SimpleNamespace(message_id=self.next_message_id)
        self.next_message_id += 1
        self.sent.append((chat_id, text, reply_markup, parse_mode))
        return message


class FakeIsolation:
    @asynccontextmanager
    async def lock(self, key):
        yield


class FakeUIRepository:
    def __init__(self):
        self.saved = []

    async def get_ui_message_ids(self, user_id):
        return 200, 300

    async def save_ui_message_ids(
        self,
        user_id,
        title_message_id,
        greeting_message_id,
    ):
        self.saved.append(
            (user_id, title_message_id, greeting_message_id)
        )


def test_due_session_is_reset_and_keeps_existing_greeting(monkeypatch):
    async def unread_notifications(user_id):
        return 0

    monkeypatch.setattr(
        session_module.notify_repo,
        "count_unread_messages",
        unread_notifications,
    )

    async def scenario():
        redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
        storage = RedisStorage(
            redis=redis,
            key_builder=DefaultKeyBuilder(
                prefix="test:pomogator:fsm",
                with_bot_id=True,
            ),
        )
        service = SessionActivityService(
            redis=redis,
            storage=storage,
            isolation=FakeIsolation(),
            timeout_seconds=24 * 60 * 60,
            check_interval_seconds=60,
            ui_repository=FakeUIRepository(),
        )
        bot = FakeBot()
        service._bot = bot

        key = StorageKey(bot_id=9, chat_id=20, user_id=10)
        state = FSMContext(storage=storage, key=key)
        await state.set_state(CardMaking.tutor_price)
        await state.update_data(
            **{
                MessageCleaner.STORAGE_KEY: [100],
                MessageCleaner.GREETING_STORAGE_KEY: 300,
                TitleManager.STORAGE_KEY: 200,
                "tutor_price": 1500,
            }
        )
        member = service._member(9, 20, 10)
        await redis.zadd(
            service.ACTIVITY_KEY,
            {member: time.time() - service.timeout_seconds - 1},
        )

        await service.process_due_sessions()
        result = (
            await state.get_state(),
            await state.get_data(),
            await redis.zscore(service.ACTIVITY_KEY, member),
            bot,
            service.ui_repository.saved,
        )
        await storage.close()
        return result

    current_state, data, activity_score, bot, saved = asyncio.run(scenario())

    assert current_state == BotFlow.menu_navigation.state
    assert data[MessageCleaner.GREETING_STORAGE_KEY] == 300
    assert data[TitleManager.STORAGE_KEY] == 1000
    assert "tutor_price" not in data
    assert activity_score is not None
    assert activity_score > time.time() - 60
    assert (20, 100) in bot.deleted
    assert (20, 200) in bot.deleted
    assert len(bot.sent) == 1
    assert bot.sent[0][1] == "Главное меню"
    assert bot.sent[0][2] is not None
    assert saved == [(10, 1000, 300)]
