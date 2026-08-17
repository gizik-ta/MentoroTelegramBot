import asyncio
from types import SimpleNamespace

from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage
from common.utils.title_manager import TitleManager
from features.user_menu.keyboards import UserMenuKeyboards


class FakeBot:
    def __init__(self) -> None:
        self.edited = []
        self.sent = []
        self.deleted = []
        self.operations = []
        self.next_message_id = 900

    async def edit_message_text(self, **kwargs):
        self.edited.append(kwargs)

    async def send_message(self, **kwargs):
        self.sent.append(kwargs)
        self.operations.append(("send", kwargs["text"]))
        message = SimpleNamespace(message_id=self.next_message_id)
        self.next_message_id += 1
        return message

    async def delete_message(self, **kwargs):
        self.deleted.append(kwargs)
        self.operations.append(("delete", kwargs["message_id"]))


def test_ordinary_title_update_replaces_title_and_reply_keyboard():
    async def scenario():
        state = FSMContext(
            storage=MemoryStorage(),
            key=StorageKey(bot_id=9, chat_id=20, user_id=10),
        )
        await state.update_data(**{TitleManager.STORAGE_KEY: 200})
        bot = FakeBot()

        result = await TitleManager.update(
            bot=bot,
            chat_id=20,
            state=state,
            text="Главное меню",
            reply_markup=UserMenuKeyboards.user_menu_keyboard(),
        )
        return result, await state.get_data(), bot

    result, data, bot = asyncio.run(scenario())

    assert result == 900
    assert data[TitleManager.STORAGE_KEY] == 900
    assert bot.edited == []
    assert bot.deleted == [{"chat_id": 20, "message_id": 200}]
    assert bot.sent[0]["text"] == "Главное меню"
    assert bot.sent[0]["reply_markup"] is not None
    assert bot.operations == [("send", "Главное меню"), ("delete", 200)]


def test_each_stage_change_gets_a_new_title_message_id():
    async def scenario():
        state = FSMContext(
            storage=MemoryStorage(),
            key=StorageKey(bot_id=9, chat_id=20, user_id=10),
        )
        bot = FakeBot()
        keyboard = UserMenuKeyboards.user_menu_keyboard()

        created_id = await TitleManager.update(
            bot=bot,
            chat_id=20,
            state=state,
            text="Главное меню",
            reply_markup=keyboard,
        )
        edited_id = await TitleManager.update(
            bot=bot,
            chat_id=20,
            state=state,
            text="Мои объявления",
            reply_markup=UserMenuKeyboards.back_to_menu_keyboard(),
        )
        return created_id, edited_id, await state.get_data(), bot

    created_id, edited_id, data, bot = asyncio.run(scenario())

    assert created_id == 900
    assert edited_id == 901
    assert data[TitleManager.STORAGE_KEY] == 901
    assert bot.sent[0]["text"] == "Главное меню"
    assert bot.sent[0]["reply_markup"] is not None
    assert bot.sent[1]["text"] == "Мои объявления"
    assert bot.sent[1]["reply_markup"] is not None
    assert bot.deleted == [{"chat_id": 20, "message_id": 900}]
    assert bot.edited == []


def test_afk_title_update_replaces_title_explicitly():
    async def scenario():
        state = FSMContext(
            storage=MemoryStorage(),
            key=StorageKey(bot_id=9, chat_id=20, user_id=10),
        )
        await state.update_data(**{TitleManager.STORAGE_KEY: 200})
        bot = FakeBot()

        result = await TitleManager.update(
            bot=bot,
            chat_id=20,
            state=state,
            text="Главное меню",
            reply_markup=UserMenuKeyboards.user_menu_keyboard(),
            force_replace=True,
        )
        return result, await state.get_data(), bot

    result, data, bot = asyncio.run(scenario())

    assert result == 900
    assert data[TitleManager.STORAGE_KEY] == 900
    assert bot.edited == []
    assert bot.sent[0]["text"] == "Главное меню"
    assert bot.sent[0]["reply_markup"] is not None
    assert bot.deleted == [{"chat_id": 20, "message_id": 200}]
    assert bot.operations == [("delete", 200), ("send", "Главное меню")]
