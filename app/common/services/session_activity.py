import asyncio
import time

import aiosqlite
from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import BaseEventIsolation, StorageKey
from aiogram.fsm.storage.redis import RedisStorage
from common.utils.cleaner import MessageCleaner
from common.utils.title_manager import TitleManager
from features.common.states import BotFlow
from features.starting.texts import StartTexts
from features.user_menu.rendering import UserMenuViews
from infrastructure.database import notify_repo, user_repo
from infrastructure.database.repositories.user_repo import UserRepository
from redis.asyncio import Redis
from redis.exceptions import RedisError


class SessionActivityService:
    """Reset Redis-backed Telegram sessions before their messages become too old."""

    ACTIVITY_KEY = "pomogator:session:last_activity"

    def __init__(
        self,
        redis: Redis,
        storage: RedisStorage,
        isolation: BaseEventIsolation,
        timeout_seconds: int,
        check_interval_seconds: int = 60,
        ui_repository: UserRepository = user_repo,
    ) -> None:
        self.redis = redis
        self.storage = storage
        self.isolation = isolation
        self.timeout_seconds = timeout_seconds
        self.check_interval_seconds = min(max(check_interval_seconds, 1), 60)
        self.ui_repository = ui_repository
        self._stop_event = asyncio.Event()
        self._task: asyncio.Task | None = None
        self._bot: Bot | None = None

    async def touch(self, bot_id: int, chat_id: int, user_id: int) -> None:
        await self.redis.zadd(
            self.ACTIVITY_KEY,
            {self._member(bot_id, chat_id, user_id): time.time()},
        )

    async def start(self, bot: Bot) -> None:
        await self.redis.ping()
        self._bot = bot
        self._stop_event.clear()
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(
                self._run(),
                name="pomogator-afk-session-reset",
            )

    async def stop(self) -> None:
        self._stop_event.set()
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None

    async def process_due_sessions(self) -> None:
        if self._bot is None:
            return

        cutoff = time.time() - self.timeout_seconds
        members = await self.redis.zrangebyscore(
            self.ACTIVITY_KEY,
            min="-inf",
            max=cutoff,
            start=0,
            num=100,
        )
        for raw_member in members:
            member = (
                raw_member.decode("utf-8")
                if isinstance(raw_member, bytes)
                else str(raw_member)
            )
            parsed = self._parse_member(member)
            if parsed is None:
                await self.redis.zrem(self.ACTIVITY_KEY, member)
                continue
            await self._reset_if_still_due(*parsed, member=member, cutoff=cutoff)

    async def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                await self.process_due_sessions()
            except asyncio.CancelledError:
                raise
            except (
                OSError,
                RuntimeError,
                TelegramAPIError,
                RedisError,
                aiosqlite.Error,
            ):
                # Redis and Telegram failures are retried on the next short cycle.
                await asyncio.sleep(0)

            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=self.check_interval_seconds,
                )
            except TimeoutError:
                pass

    async def _reset_if_still_due(
        self,
        bot_id: int,
        chat_id: int,
        user_id: int,
        *,
        member: str,
        cutoff: float,
    ) -> None:
        if self._bot is None or bot_id != self._bot.id:
            return

        key = StorageKey(bot_id=bot_id, chat_id=chat_id, user_id=user_id)
        async with self.isolation.lock(key=key):
            last_activity = await self.redis.zscore(self.ACTIVITY_KEY, member)
            if last_activity is None or last_activity > cutoff:
                return

            state = FSMContext(storage=self.storage, key=key)
            data = await state.get_data()
            stored_title_id, stored_greeting_id = (
                await self.ui_repository.get_ui_message_ids(user_id)
            )
            title_id = data.get(TitleManager.STORAGE_KEY) or stored_title_id
            greeting_id = (
                data.get(MessageCleaner.GREETING_STORAGE_KEY) or stored_greeting_id
            )
            await state.update_data(
                **{
                    TitleManager.STORAGE_KEY: title_id,
                    MessageCleaner.GREETING_STORAGE_KEY: greeting_id,
                }
            )

            await MessageCleaner.clear_all_state_messages(
                self._bot,
                chat_id,
                state,
            )
            await MessageCleaner.clear_state_preserving(
                state,
                TitleManager.STORAGE_KEY,
                MessageCleaner.GREETING_STORAGE_KEY,
            )

            if not greeting_id:
                greeting = await self._bot.send_message(
                    chat_id=chat_id,
                    text=StartTexts.GREETINGS_MESSAGE,
                )
                await state.update_data(
                    **{MessageCleaner.GREETING_STORAGE_KEY: greeting.message_id}
                )

            await state.set_state(BotFlow.menu_navigation)
            try:
                unread = await notify_repo.count_unread_messages(user_id)
            except (RuntimeError, aiosqlite.Error):
                unread = 0
            title, keyboard = UserMenuViews.title(unread)
            new_title_id = await TitleManager.update(
                bot=self._bot,
                chat_id=chat_id,
                state=state,
                text=title,
                reply_markup=keyboard,
                force_replace=True,
            )
            await self.ui_repository.save_ui_message_ids(
                user_id,
                new_title_id,
                greeting_id,
            )
            # Keep an idle session scheduled so its menu title is refreshed every day.
            await self.redis.zadd(self.ACTIVITY_KEY, {member: time.time()})

    @staticmethod
    def _member(bot_id: int, chat_id: int, user_id: int) -> str:
        return f"{bot_id}:{chat_id}:{user_id}"

    @staticmethod
    def _parse_member(member: str) -> tuple[int, int, int] | None:
        try:
            bot_id, chat_id, user_id = member.split(":", maxsplit=2)
            return int(bot_id), int(chat_id), int(user_id)
        except (TypeError, ValueError):
            return None
