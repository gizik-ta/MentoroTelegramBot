from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from common.utils.cleaner import MessageCleaner
from common.utils.title_manager import TitleManager
from features.common.callbacks import AdActionCallback
from features.common.states import BotFlow
from features.common.texts import CommonTexts
from features.user_menu.rendering import UserMenuViews
from features.user_menu.texts import UserMenuTexts
from infrastructure.database import notify_repo

from .keyboards import SavedAdKeyboards
from .services import SavedAdsServices
from .texts import SavedTexts

saved_ads_router = Router()


@saved_ads_router.message(
    BotFlow.saved_ads,
    lambda message: message.text == UserMenuTexts.TO_MENU_BTN,
)
async def back_to_menu(message: Message, state: FSMContext):
    await MessageCleaner.track(state, message.message_id)
    await MessageCleaner.purge(bot=message.bot, chat_id=message.chat.id, state=state)

    unread_notifications = await notify_repo.count_unread_messages(message.from_user.id)
    title, keyboard = UserMenuViews.title(unread_notifications)

    await state.set_state(BotFlow.menu_navigation)
    await TitleManager.update(
        bot=message.bot,
        chat_id=message.chat.id,
        state=state,
        text=title,
        reply_markup=keyboard,
    )


@saved_ads_router.callback_query(
    BotFlow.saved_ads,
    AdActionCallback.filter(F.action.in_({"like", "unlike"})),
)
async def handle_ad_like(
    callback: CallbackQuery, callback_data: AdActionCallback, state: FSMContext
):
    user_id = callback.from_user.id
    ad_id = callback_data.ad_id
    is_like = callback_data.action == "like"

    await SavedAdsServices.set_saved(ad_id, user_id, is_like)

    await callback.message.edit_reply_markup(
        reply_markup=SavedAdKeyboards.saved_ads_processing(
            ad_id=ad_id, is_liked=is_like
        )
    )
    toast_text = CommonTexts.TOAST_SAVED if is_like else CommonTexts.TOAST_REMOVED
    await callback.answer(toast_text)


@saved_ads_router.callback_query(
    BotFlow.saved_ads,
    AdActionCallback.filter(F.action == "contact"),
)
async def handle_ad_contact(
    callback: CallbackQuery, callback_data: AdActionCallback, state: FSMContext
):
    username = await SavedAdsServices.get_contact_username(callback_data.ad_id)
    text = SavedTexts.contact_info_text(username)

    prompt = await callback.message.answer(text)
    await MessageCleaner.track(state, prompt.message_id)
    await callback.answer()
