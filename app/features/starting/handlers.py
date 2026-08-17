from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from common.utils.cleaner import MessageCleaner
from common.utils.title_manager import TitleManager
from features.admin.rendering import AdminRendering
from features.admin.services import AdminViewServices
from features.admin.states import AdminFlow
from features.common.states import BotFlow
from features.notifications.texts import NotificationMessagesTemplates
from features.user_menu.rendering import UserMenuViews
from infrastructure.database import ad_service, notify_repo, user_repo

from .texts import StartTexts

starting_router = Router()


@starting_router.message(CommandStart())
async def starting_handler(message: Message, state: FSMContext):
    await MessageCleaner.track(state, message.message_id)
    data = await state.get_data()
    greeting_id = data.get(MessageCleaner.GREETING_STORAGE_KEY)
    await MessageCleaner.clear_all_state_messages(
        message.bot,
        message.chat.id,
        state,
    )
    await MessageCleaner.clear_state_preserving(
        state,
        TitleManager.STORAGE_KEY,
        MessageCleaner.GREETING_STORAGE_KEY,
    )

    await user_repo.add_user(message.from_user.id)

    if AdminViewServices.is_admin(message.from_user.id):
        await state.set_state(AdminFlow.menu_navigation)
        title, keyboard = AdminRendering.title()
        await TitleManager.update(
            bot=message.bot,
            chat_id=message.chat.id,
            state=state,
            text=title,
            reply_markup=keyboard,
        )
        return

    if not greeting_id:
        greeting = await message.answer(text=StartTexts.GREETINGS_MESSAGE)
        await state.update_data(
            **{MessageCleaner.GREETING_STORAGE_KEY: greeting.message_id}
        )

    await state.set_state(BotFlow.menu_navigation)

    should_notify_about_trial = await ad_service.ensure_free_trial_entitlement(
        message.from_user.id,
        message.from_user.username,
    )
    if should_notify_about_trial:
        await notify_repo.send_notification(
            user_id=message.from_user.id,
            notification_text=(NotificationMessagesTemplates.USING_POMOGATOR_GRATITUDE),
        )

    unread_notifications = await notify_repo.count_unread_messages(message.from_user.id)

    title, keyboard = UserMenuViews.title(unread_notifications)
    await TitleManager.update(
        bot=message.bot,
        chat_id=message.chat.id,
        state=state,
        text=title,
        reply_markup=keyboard,
    )
