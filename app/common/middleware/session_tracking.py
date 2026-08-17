from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware, Dispatcher
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, TelegramObject
from common.services.session_activity import SessionActivityService
from common.utils.cleaner import MessageCleaner
from common.utils.title_manager import TitleManager
from infrastructure.database import user_repo
from infrastructure.database.repositories.user_repo import UserRepository


class SessionTrackingMiddleware(BaseMiddleware):
    """Persist activity and every incoming message, including unmatched input."""

    def __init__(
        self,
        activity_service: SessionActivityService,
        ui_repository: UserRepository | None = None,
    ) -> None:
        self.activity_service = activity_service
        self.ui_repository = ui_repository

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        state = data.get("state")
        user = data.get("event_from_user") or getattr(event, "from_user", None)
        if (
            isinstance(state, FSMContext)
            and user is not None
            and self.ui_repository is not None
        ):
            persisted_ui_ids = await self._hydrate_ui_message_ids(state, user.id)
            ui_ids_before = await self._ui_message_ids(state)
        else:
            persisted_ui_ids = (None, None)
            ui_ids_before = (None, None)

        if isinstance(event, Message) and isinstance(state, FSMContext):
            await MessageCleaner.track(state, event.message_id)

        chat = data.get("event_chat") or getattr(event, "chat", None)
        bot = data.get("bot") or getattr(event, "bot", None)
        if user is not None and chat is not None and bot is not None:
            await self.activity_service.touch(
                bot_id=bot.id,
                chat_id=chat.id,
                user_id=user.id,
            )

        try:
            return await handler(event, data)
        finally:
            if (
                isinstance(state, FSMContext)
                and user is not None
                and self.ui_repository is not None
            ):
                ui_ids_after = await self._ui_message_ids(state)
                if (
                    ui_ids_after != ui_ids_before
                    or ui_ids_after != persisted_ui_ids
                ):
                    await self._persist_ui_message_ids(
                        user.id,
                        *ui_ids_after,
                    )

    async def _hydrate_ui_message_ids(
        self,
        state: FSMContext,
        user_id: int,
    ) -> tuple[int | None, int | None]:
        data = await state.get_data()
        title_id, greeting_id = await self.ui_repository.get_ui_message_ids(user_id)
        restored = {}
        if not data.get(TitleManager.STORAGE_KEY) and title_id is not None:
            restored[TitleManager.STORAGE_KEY] = title_id
        if not data.get(MessageCleaner.GREETING_STORAGE_KEY) and greeting_id is not None:
            restored[MessageCleaner.GREETING_STORAGE_KEY] = greeting_id
        if restored:
            await state.update_data(**restored)
        return title_id, greeting_id

    @staticmethod
    async def _ui_message_ids(
        state: FSMContext,
    ) -> tuple[int | None, int | None]:
        data = await state.get_data()
        return (
            data.get(TitleManager.STORAGE_KEY),
            data.get(MessageCleaner.GREETING_STORAGE_KEY),
        )

    async def _persist_ui_message_ids(
        self,
        user_id: int,
        title_message_id: int | None,
        greeting_message_id: int | None,
    ) -> None:
        await self.ui_repository.save_ui_message_ids(
            user_id,
            title_message_id,
            greeting_message_id,
        )


def register_session_tracking(
    dispatcher: Dispatcher,
    activity_service: SessionActivityService,
) -> None:
    middleware = SessionTrackingMiddleware(activity_service, user_repo)
    dispatcher.message.outer_middleware(middleware)
    dispatcher.callback_query.outer_middleware(middleware)
