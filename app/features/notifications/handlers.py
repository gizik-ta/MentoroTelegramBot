import logging

from aiogram import Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from common.utils.cleaner import MessageCleaner
from common.utils.title_manager import TitleManager
from features.common.states import BotFlow
from features.user_menu.rendering import UserMenuViews
from features.user_menu.texts import UserMenuTexts

from .callbacks import DeleteNotificationCallback
from .service import NotificationService
from .texts import NotificationsTexts

notifications_router = Router()
logger = logging.getLogger(__name__)


@notifications_router.message(
    BotFlow.notifications, lambda message: message.text == UserMenuTexts.TO_MENU_BTN
)
async def back_to_menu(message: Message, state: FSMContext):
    await MessageCleaner.track(state, message.message_id)
    await MessageCleaner.purge(bot=message.bot, chat_id=message.chat.id, state=state)

    title, keyboard = UserMenuViews.title(0)

    await state.set_state(BotFlow.menu_navigation)
    await TitleManager.update(
        bot=message.bot,
        chat_id=message.chat.id,
        state=state,
        text=title,
        reply_markup=keyboard,
    )


@notifications_router.callback_query(
    BotFlow.notifications, DeleteNotificationCallback.filter()
)
async def delete_notification(
    callback: CallbackQuery,
    callback_data: DeleteNotificationCallback,
    state: FSMContext,
):
    deleted = await NotificationService.delete_owned(
        callback_data.id,
        callback.from_user.id,
    )

    if not deleted:
        await callback.answer(NotificationsTexts.NOT_FOUND, show_alert=True)
        return

    await callback.answer(NotificationsTexts.DELETE_SUCCESS)

    try:
        await callback.bot.delete_message(
            chat_id=callback.message.chat.id,
            message_id=callback.message.message_id,
        )
        await MessageCleaner.untrack(
            state=state,
            message_id=callback.message.message_id,
        )
    except TelegramBadRequest as e:
        logger.info(
            "Notification %s was deleted from DB but message %s "
            "could not be deleted: %s",
            callback_data.id,
            callback.message.message_id,
            e,
        )
