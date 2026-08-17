from aiogram import Bot, F, Router, types
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from common.utils.cleaner import MessageCleaner
from common.utils.title_manager import TitleManager
from features.common.callbacks import (
    ClassesFormatCallback,
    SubjectSelectCallback,
    TeachingTypeCallback,
)
from features.common.states import BotFlow
from features.tutor_searching.services.feed_service import FeedService
from features.user_menu.keyboards import UserMenuKeyboards
from features.user_menu.texts import UserMenuTexts
from infrastructure.database import notify_repo

from .callbacks import (
    AdActionCallback,
    FilterCallback,
    PaginationCallback,
)
from .keyboards import TutorSearchingKeyboards
from .rendering import TutorSearchingViews
from .states import TutorSearch
from .texts import TutorSearchingTexts

tutor_searching_router = Router()

# --- Navigation Handlers ---


@tutor_searching_router.message(
    StateFilter(TutorSearch), F.text == UserMenuTexts.TO_MENU_BTN
)
async def back_to_menu(message: types.Message, state: FSMContext, bot: Bot):
    await MessageCleaner.track(state, message.message_id)

    await MessageCleaner.clear_all_state_messages(bot, message.chat.id, state)
    await MessageCleaner.clear_state_preserving(
        state,
        TitleManager.STORAGE_KEY,
        MessageCleaner.GREETING_STORAGE_KEY,
    )

    await state.set_state(BotFlow.menu_navigation)

    unread_notifications = await notify_repo.count_unread_messages(message.from_user.id)

    await TitleManager.update(
        bot=message.bot,
        chat_id=message.chat.id,
        state=state,
        text=TutorSearchingTexts.MAIN_MENU_TITLE,
        reply_markup=UserMenuKeyboards.user_menu_keyboard(unread_notifications),
    )


@tutor_searching_router.callback_query(
    TutorSearch.subject_processing, SubjectSelectCallback.filter()
)
async def process_subject_selection(
    callback: types.CallbackQuery,
    callback_data: SubjectSelectCallback,
    state: FSMContext,
    bot: Bot,
):
    await FeedService.select_subject(callback, state, bot, callback_data.value)
    await callback.answer()


# --- Filter Selection Handlers ---


@tutor_searching_router.callback_query(
    StateFilter(TutorSearch), FilterCallback.filter(F.action == "set")
)
async def open_filter_prompt(
    callback: types.CallbackQuery,
    callback_data: FilterCallback,
    state: FSMContext,
    bot: Bot,
):
    filter_name = callback_data.name
    prompt_text, keyboard = TutorSearchingViews.filters_prompts(filter_name)

    await MessageCleaner.purge(bot, callback.message.chat.id, state)
    if not await FeedService.open_filter(state, filter_name):
        await callback.answer()
        return

    prompt_msg = await callback.message.answer(prompt_text, reply_markup=keyboard)
    await MessageCleaner.track(state, prompt_msg.message_id)
    await callback.answer()


@tutor_searching_router.callback_query(
    StateFilter(TutorSearch), FilterCallback.filter(F.action == "delete")
)
async def remove_filter(
    callback: types.CallbackQuery,
    callback_data: FilterCallback,
    state: FSMContext,
    bot: Bot,
):
    filter_name = callback_data.name
    await FeedService.remove_filter(state, filter_name)
    await FeedService.refresh(callback, state, bot, callback.from_user.id)
    await callback.answer()


@tutor_searching_router.message(TutorSearch.price_filter, F.text)
async def process_price_input(message: types.Message, state: FSMContext, bot: Bot):
    if not message.text.isdigit():
        invalid_msg = await message.answer(TutorSearchingTexts.INVALID_PRICE_INPUT)
        await MessageCleaner.track(state, message.message_id)
        await MessageCleaner.track(state, invalid_msg.message_id)
        return

    price_val = int(message.text)
    await MessageCleaner.track(state, message.message_id)
    await FeedService.set_filter(state, "price", price_val)
    await FeedService.refresh(message, state, bot, message.from_user.id)


@tutor_searching_router.callback_query(
    TutorSearch.classes_format_filter, ClassesFormatCallback.filter()
)
async def process_classes_format_filter(
    callback: types.CallbackQuery,
    callback_data: ClassesFormatCallback,
    state: FSMContext,
    bot: Bot,
):
    await FeedService.set_filter(state, "classes_format", callback_data.value)
    await FeedService.refresh(callback, state, bot, callback.from_user.id)
    await callback.answer()


@tutor_searching_router.callback_query(
    TutorSearch.teaching_type_filter, TeachingTypeCallback.filter()
)
async def process_teaching_type_filter(
    callback: types.CallbackQuery,
    callback_data: TeachingTypeCallback,
    state: FSMContext,
    bot: Bot,
):
    await FeedService.set_filter(state, "teaching_type", callback_data.value)
    await FeedService.refresh(callback, state, bot, callback.from_user.id)
    await callback.answer()


# --- Feed Actions & Pagination ---


@tutor_searching_router.callback_query(
    StateFilter(TutorSearch), PaginationCallback.filter()
)
async def handle_feed_pagination(
    callback: types.CallbackQuery,
    callback_data: PaginationCallback,
    state: FSMContext,
    bot: Bot,
):
    shifted = await FeedService.shift_page(
        state,
        callback_data.direction,
        expected_index=callback_data.index,
    )
    if not shifted:
        await callback.answer()
        return
    await FeedService.refresh(
        callback,
        state,
        bot,
        callback.from_user.id,
        reset_index=False,
    )
    await callback.answer()


@tutor_searching_router.callback_query(
    StateFilter(TutorSearch), AdActionCallback.filter(F.action.in_({"like", "unlike"}))
)
async def handle_ad_like(
    callback: types.CallbackQuery, callback_data: AdActionCallback, state: FSMContext
):
    user_id = callback.from_user.id
    ad_id = callback_data.ad_id
    is_like = callback_data.action == "like"

    await FeedService.set_like(ad_id, user_id, is_like)

    data = await state.get_data()
    ad_ids = data.get("cached_ad_ids", [])
    current_idx = data.get("current_ad_index", 0)

    await callback.message.edit_reply_markup(
        reply_markup=TutorSearchingKeyboards.ads_actions_keyboard(
            current_index=current_idx,
            total_count=len(ad_ids),
            ad_id=ad_id,
            is_liked=is_like,
        )
    )
    toast_text = (
        TutorSearchingTexts.TOAST_SAVED
        if is_like
        else TutorSearchingTexts.TOAST_REMOVED
    )
    await callback.answer(toast_text)


@tutor_searching_router.callback_query(
    StateFilter(TutorSearch), AdActionCallback.filter(F.action == "contact")
)
async def handle_ad_contact(
    callback: types.CallbackQuery, callback_data: AdActionCallback, state: FSMContext
):
    username = await FeedService.get_contact_username(callback_data.ad_id)
    text = TutorSearchingViews.contact_info_text(username)

    prompt = await callback.message.answer(text)
    await MessageCleaner.track(state, prompt.message_id)
    await callback.answer()
