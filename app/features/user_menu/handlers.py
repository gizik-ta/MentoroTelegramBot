from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from common.utils.cleaner import MessageCleaner
from common.utils.title_manager import TitleManager
from features.common.states import BotFlow
from features.my_ads.rendering import MyAdsRendering
from features.notifications.rendering import NotificationsViews
from features.saved.rendering import SavedViews
from features.saved.services import SavedAdsServices
from features.tutor_searching.rendering import TutorSearchingViews
from features.tutor_searching.states import TutorSearch
from infrastructure.database import notify_repo

from .texts import UserMenuTexts

user_menu_router = Router()

# =========================
# Find tutor
# =========================


@user_menu_router.message(
    BotFlow.menu_navigation,
    lambda message: message.text == UserMenuTexts.TUTOR_SEARCH_BTN,
)
async def entering_tutor_search_handler(message: Message, state: FSMContext):
    await MessageCleaner.track(state, message.message_id)
    await MessageCleaner.purge(message.bot, message.chat.id, state)

    title, keyboard = TutorSearchingViews.title()

    await state.set_state(TutorSearch.subject_processing)
    await TitleManager.update(
        message.bot, message.chat.id, state, text=title, reply_markup=keyboard
    )

    text, keyboard = TutorSearchingViews.subject()
    subject_q = await message.answer(text, reply_markup=keyboard)
    await state.update_data(main_message_id=subject_q.message_id)


# =========================
# Notifications
# =========================


@user_menu_router.message(
    BotFlow.menu_navigation,
    lambda message: UserMenuTexts.NOTIFICATIONS_BTN in message.text,
)
async def entering_notifications_handler(message: Message, state: FSMContext):
    await MessageCleaner.track(state, message.message_id)
    await MessageCleaner.purge(bot=message.bot, chat_id=message.chat.id, state=state)

    title, keyboard = NotificationsViews.title()

    await state.set_state(BotFlow.notifications)
    await TitleManager.update(
        bot=message.bot,
        chat_id=message.chat.id,
        state=state,
        text=title,
        reply_markup=keyboard,
    )

    notifications = await notify_repo.get_notifications(message.from_user.id)
    for notification in notifications:
        text, keyboard = NotificationsViews.notification_view(notification)
        notify_message = await message.answer(text, reply_markup=keyboard)
        await notify_repo.mark_as_read(notification.notification_id)
        await MessageCleaner.track(state, notify_message.message_id)


# =========================
# Saved ads
# =========================


@user_menu_router.message(
    BotFlow.menu_navigation, lambda message: message.text == UserMenuTexts.SAVED_ADS_BTN
)
async def entering_saved_messages(message: Message, state: FSMContext):
    await MessageCleaner.track(state, message.message_id)
    await MessageCleaner.purge(bot=message.bot, chat_id=message.chat.id, state=state)

    title, keyboard = SavedViews.title()

    await state.set_state(BotFlow.saved_ads)
    await TitleManager.update(
        bot=message.bot,
        chat_id=message.chat.id,
        state=state,
        text=title,
        reply_markup=keyboard,
    )

    saved_ads = await SavedAdsServices.get_user_ads(message.from_user.id)
    message_ids = await SavedViews.show_ads(message, saved_ads)
    await MessageCleaner.track(state, message_ids)


# =========================
# My ads
# =========================
@user_menu_router.message(
    BotFlow.menu_navigation, lambda message: message.text == UserMenuTexts.MY_ADS_BTN
)
async def entering_my_ads_state(message: Message, state: FSMContext):
    await MessageCleaner.track(state, message.message_id)
    await MessageCleaner.purge(bot=message.bot, chat_id=message.chat.id, state=state)

    title, keyboard = MyAdsRendering.title()

    await state.set_state(BotFlow.my_ads)
    await TitleManager.update(
        bot=message.bot,
        chat_id=message.chat.id,
        state=state,
        text=title,
        reply_markup=keyboard,
    )

    description_id = await MyAdsRendering.description(message)
    await MessageCleaner.track(state, description_id)

    user_ads = await MyAdsRendering.show_user_ads(
        user_id=message.from_user.id,
        message=message,
        state=state,
        show_state=True,
        show_statistic=True,
    )
    if user_ads:
        for ad_id, message_ids in user_ads:
            await state.update_data(**{f"ad_{ad_id}": message_ids})
            await MessageCleaner.track(state, message_ids)
