from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from common.utils.cleaner import MessageCleaner
from common.utils.title_manager import TitleManager
from features.common.states import BotFlow
from features.user_menu.rendering import UserMenuViews

from .callbacks import ModerationCallback, RejectionCallback
from .rendering import AdminRendering
from .services import (
    AdminModerationServices,
    AdminStatisticsServices,
    AdminViewServices,
    AdminWarningServices,
)
from .states import AdminFlow
from .texts import AdminTexts

admin_router = Router()


async def _show_admin_menu(message: Message, state: FSMContext) -> None:
    await MessageCleaner.purge(message.bot, message.chat.id, state)
    await state.set_state(AdminFlow.menu_navigation)
    await state.update_data(
        rejection_ad_id=None,
        rejection_reason=None,
        rejection_prompt_message_id=None,
    )
    title, keyboard = AdminRendering.title()
    await TitleManager.update(
        message.bot,
        message.chat.id,
        state,
        title,
        keyboard,
    )


async def _show_moderation_queue(message: Message, state: FSMContext) -> None:
    await MessageCleaner.purge(message.bot, message.chat.id, state)
    await state.set_state(AdminFlow.ad_checking)
    await state.update_data(
        rejection_ad_id=None,
        rejection_reason=None,
        rejection_prompt_message_id=None,
    )

    title, keyboard = AdminRendering.moderation_title()
    await TitleManager.update(
        message.bot,
        message.chat.id,
        state,
        title,
        keyboard,
    )

    ads = await AdminModerationServices.get_ads_on_check()
    message_ids = await AdminRendering.moderation_queue(message, ads)
    await MessageCleaner.track(state, message_ids)


async def _show_statistics(message: Message, state: FSMContext) -> None:
    await MessageCleaner.purge(message.bot, message.chat.id, state)
    await state.set_state(AdminFlow.statistics)

    title, keyboard = AdminRendering.statistics_title()
    await TitleManager.update(
        message.bot,
        message.chat.id,
        state,
        title,
        keyboard,
    )
    statistics = await AdminStatisticsServices.get_statistics()
    statistics_message = await message.answer(AdminRendering.statistics(statistics))
    await MessageCleaner.track(state, statistics_message.message_id)


async def _show_admin_notifications(message: Message, state: FSMContext) -> None:
    await MessageCleaner.purge(message.bot, message.chat.id, state)
    await state.set_state(AdminFlow.notifications)

    title, keyboard = AdminRendering.notifications_title()
    await TitleManager.update(
        message.bot,
        message.chat.id,
        state,
        title,
        keyboard,
    )
    warnings = await AdminWarningServices.get_warnings()
    message_ids = []
    for warning_text in AdminRendering.warnings(warnings):
        warning = await message.answer(warning_text)
        message_ids.append(warning.message_id)
    await MessageCleaner.track(state, message_ids)


async def _admin_message_allowed(message: Message, state: FSMContext) -> bool:
    if AdminViewServices.is_admin(message.from_user.id):
        return True
    denied = await message.answer(AdminTexts.ACCESS_DENIED)
    await MessageCleaner.track(state, denied.message_id)
    return False


async def _admin_callback_allowed(callback: CallbackQuery) -> bool:
    if AdminViewServices.is_admin(callback.from_user.id):
        return True
    await callback.answer(AdminTexts.ACCESS_DENIED, show_alert=True)
    return False


@admin_router.message(BotFlow.menu_navigation, Command("admin_view"))
async def enter_admin_view(message: Message, state: FSMContext) -> None:
    if not await _admin_message_allowed(message, state):
        return

    await MessageCleaner.track(state, message.message_id)
    await _show_admin_menu(message, state)


@admin_router.message(AdminFlow.menu_navigation, Command("user_view"))
async def enter_user_view(message: Message, state: FSMContext) -> None:
    if not await _admin_message_allowed(message, state):
        return

    await MessageCleaner.track(state, message.message_id)
    await MessageCleaner.purge(message.bot, message.chat.id, state)
    await state.set_state(BotFlow.menu_navigation)
    notifications = await AdminViewServices.unread_notifications(message.from_user.id)
    title, keyboard = UserMenuViews.title(notifications)
    await TitleManager.update(
        message.bot,
        message.chat.id,
        state,
        title,
        keyboard,
    )


@admin_router.message(
    AdminFlow.menu_navigation,
    F.text == AdminTexts.CHECK_ADS_BUTTON,
)
async def open_moderation_queue(message: Message, state: FSMContext) -> None:
    if not await _admin_message_allowed(message, state):
        return

    await MessageCleaner.track(state, message.message_id)
    await _show_moderation_queue(message, state)


@admin_router.message(
    AdminFlow.menu_navigation,
    F.text == AdminTexts.STATISTICS_BUTTON,
)
async def open_statistics(message: Message, state: FSMContext) -> None:
    if not await _admin_message_allowed(message, state):
        return

    await MessageCleaner.track(state, message.message_id)
    await _show_statistics(message, state)


@admin_router.message(
    AdminFlow.menu_navigation,
    F.text == AdminTexts.NOTIFICATIONS_BUTTON,
)
async def open_admin_notifications(message: Message, state: FSMContext) -> None:
    if not await _admin_message_allowed(message, state):
        return

    await MessageCleaner.track(state, message.message_id)
    await _show_admin_notifications(message, state)


@admin_router.message(
    StateFilter(
        AdminFlow.ad_checking,
        AdminFlow.rejection_reason,
        AdminFlow.statistics,
        AdminFlow.notifications,
    ),
    F.text == AdminTexts.BACK_TO_MENU_BUTTON,
)
async def back_to_admin_menu(message: Message, state: FSMContext) -> None:
    if not await _admin_message_allowed(message, state):
        return

    await MessageCleaner.track(state, message.message_id)
    await _show_admin_menu(message, state)


@admin_router.callback_query(
    AdminFlow.ad_checking,
    ModerationCallback.filter(F.action == "approve"),
)
async def approve_ad(
    callback: CallbackQuery,
    callback_data: ModerationCallback,
    state: FSMContext,
) -> None:
    if not await _admin_callback_allowed(callback):
        return

    ad = await AdminModerationServices.approve(callback_data.ad_id)
    if ad is None:
        await callback.answer(AdminTexts.AD_ALREADY_PROCESSED, show_alert=True)
        await _show_moderation_queue(callback.message, state)
        return

    await callback.answer(AdminTexts.AD_APPROVED)
    await _show_moderation_queue(callback.message, state)


@admin_router.callback_query(
    AdminFlow.ad_checking,
    ModerationCallback.filter(F.action == "reject"),
)
async def ask_rejection_reason(
    callback: CallbackQuery,
    callback_data: ModerationCallback,
    state: FSMContext,
) -> None:
    if not await _admin_callback_allowed(callback):
        return

    ad = await AdminModerationServices.get_ad_on_check(callback_data.ad_id)
    if ad is None:
        await callback.answer(AdminTexts.AD_ALREADY_PROCESSED, show_alert=True)
        await _show_moderation_queue(callback.message, state)
        return

    prompt_message_id = await AdminRendering.rejection_prompt(
        callback.message,
        callback_data.ad_id,
    )
    await MessageCleaner.track(state, prompt_message_id)
    await state.update_data(
        rejection_ad_id=callback_data.ad_id,
        rejection_reason=None,
        rejection_prompt_message_id=prompt_message_id,
    )
    await state.set_state(AdminFlow.rejection_reason)
    await callback.answer()


@admin_router.message(AdminFlow.rejection_reason)
async def save_rejection_reason(message: Message, state: FSMContext) -> None:
    if not await _admin_message_allowed(message, state):
        return

    await MessageCleaner.track(state, message.message_id)
    reason = message.text.strip() if message.text else ""
    if not reason:
        error = await message.answer(AdminTexts.REJECTION_REQUIRED)
        await MessageCleaner.track(state, error.message_id)
        return
    if len(reason) > 1000:
        error = await message.answer(AdminTexts.REJECTION_TOO_LONG)
        await MessageCleaner.track(state, error.message_id)
        return

    data = await state.get_data()
    ad_id = data.get("rejection_ad_id")
    prompt_message_id = data.get("rejection_prompt_message_id")
    if not isinstance(ad_id, int) or not isinstance(prompt_message_id, int):
        await _show_moderation_queue(message, state)
        return

    await state.update_data(rejection_reason=reason)
    await AdminRendering.show_rejection_reason(
        message,
        prompt_message_id,
        ad_id,
        reason,
    )


@admin_router.callback_query(
    AdminFlow.rejection_reason,
    RejectionCallback.filter(),
)
async def finish_rejection(
    callback: CallbackQuery,
    callback_data: RejectionCallback,
    state: FSMContext,
) -> None:
    if not await _admin_callback_allowed(callback):
        return

    data = await state.get_data()
    stored_ad_id = data.get("rejection_ad_id")
    if stored_ad_id != callback_data.ad_id:
        await callback.answer(AdminTexts.AD_ALREADY_PROCESSED, show_alert=True)
        return

    if callback_data.action == "cancel":
        await callback.answer(AdminTexts.REJECTION_CANCELLED)
        await _show_moderation_queue(callback.message, state)
        return

    if callback_data.action != "confirm":
        await callback.answer()
        return

    reason = data.get("rejection_reason")
    if not isinstance(reason, str) or not reason.strip():
        await callback.answer(AdminTexts.REJECTION_REQUIRED, show_alert=True)
        return

    ad = await AdminModerationServices.reject(callback_data.ad_id, reason)
    if ad is None:
        await callback.answer(AdminTexts.AD_ALREADY_PROCESSED, show_alert=True)
        await _show_moderation_queue(callback.message, state)
        return

    await callback.answer(AdminTexts.AD_REJECTED)
    await _show_moderation_queue(callback.message, state)
