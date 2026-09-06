from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InputRichMessage, Message
from common.utils.cleaner import MessageCleaner
from common.utils.title_manager import TitleManager
from features.common.states import BotFlow
from features.user_menu.rendering import UserMenuViews
from features.user_menu.texts import UserMenuTexts
from infrastructure.database import notify_repo

from .callbacks import (
    BuyAdCallback,
    DefinitelyDeleteCallback,
    DeleteAdCallback,
    RenewAdCallback,
)
from .rendering import MyAdsRendering
from .services import MyAdsServices
from .states import MyAds
from .texts import MyAdsTexts

my_ads_router = Router()


async def _send_payment_message(
    callback: CallbackQuery,
    state: FSMContext,
    *,
    ad_id: int,
    is_renewal: bool,
) -> None:
    await MessageCleaner.delete_key_messages(
        callback.message.bot,
        callback.message.chat.id,
        state,
        MessageCleaner.PAYMENT_STORAGE_KEY,
    )
    await state.set_state(BotFlow.my_ads)

    description = (
        MyAdsTexts.RENEWAL_PAYMENT_DESCRIPTION
        if is_renewal
        else MyAdsTexts.PAYMENT_DESCRIPTION
    )
    payment = await MyAdsServices.payment(
        user_id=callback.from_user.id,
        ad_id=ad_id,
        payment_type="ad_month",
        description=description,
        order_kind="renewal" if is_renewal else "initial",
    )
    await MyAdsServices.attach_ad_message(
        payment.redirect_token,
        callback.from_user.id,
        callback.message.chat.id,
        callback.message.message_id,
    )
    text, keyboard = MyAdsRendering.payment(
        payment.redirect_url,
        is_renewal=is_renewal,
    )

    payment_message = await callback.message.bot.send_rich_message(
        chat_id=callback.message.chat.id,
        rich_message=InputRichMessage(html=text),
        reply_markup=keyboard,
    )
    await MessageCleaner.track_in_key(
        state,
        MessageCleaner.PAYMENT_STORAGE_KEY,
        payment_message.message_id,
    )
    await MyAdsServices.attach_payment_message(
        payment.redirect_token,
        callback.from_user.id,
        callback.message.chat.id,
        payment_message.message_id,
    )
    await callback.answer()


@my_ads_router.callback_query(
    StateFilter(BotFlow.my_ads, MyAds.delete_ad),
    DeleteAdCallback.filter(),
)
async def ask_delete_ad(
    callback: CallbackQuery,
    callback_data: DeleteAdCallback,
    state: FSMContext,
):
    ad = await MyAdsServices.get_owned_ad(callback.from_user.id, callback_data.id)
    if ad is None:
        await callback.answer(MyAdsTexts.NOT_FOUND, show_alert=True)
        return

    await MessageCleaner.delete_key_messages(
        callback.message.bot,
        callback.message.chat.id,
        state,
        MessageCleaner.PAYMENT_STORAGE_KEY,
    )
    await state.set_state(MyAds.delete_ad)

    prompt_text, keyboard = MyAdsRendering.delete_confirmation(
        callback.message.text or "",
        callback_data.id,
    )

    await callback.message.edit_text(
        text=prompt_text,
        reply_markup=keyboard,
    )
    await callback.answer()


@my_ads_router.callback_query(MyAds.delete_ad, DefinitelyDeleteCallback.filter())
async def definitely_delete_ad(
    callback: CallbackQuery,
    callback_data: DefinitelyDeleteCallback,
    state: FSMContext,
):
    data = await state.get_data()
    action = callback_data.action
    ad_id = callback_data.id

    if action == "delete":
        deleted = await MyAdsServices.delete_owned_ad(
            user_id=callback.from_user.id,
            ad_id=ad_id,
        )
        if not deleted:
            await callback.answer(MyAdsTexts.NOT_FOUND, show_alert=True)
            await state.set_state(BotFlow.my_ads)
            return

        msg_ids = data.get(f"ad_{ad_id}", [])
        if msg_ids:
            await MessageCleaner.delete_message(
                bot=callback.message.bot,
                chat_id=callback.message.chat.id,
                state=state,
                message_id=msg_ids,
            )
        await state.update_data(**{f"ad_{ad_id}": []})
        await callback.answer(MyAdsTexts.DELETE_SUCCESS, show_alert=True)

    elif action == "back":
        ad = await MyAdsServices.get_owned_ad(callback.from_user.id, ad_id)
        if ad is None:
            await callback.answer(MyAdsTexts.NOT_FOUND, show_alert=True)
            await state.set_state(BotFlow.my_ads)
            return
        original_text, keyboard = MyAdsRendering.restore_ad(
            callback.message.text or "",
            ad_id,
            ad.is_bought,
            ad.state,
        )

        await callback.message.edit_text(
            text=original_text,
            reply_markup=keyboard,
        )
        await callback.answer()

    await state.set_state(BotFlow.my_ads)


@my_ads_router.callback_query(
    StateFilter(BotFlow.my_ads, MyAds.delete_ad),
    BuyAdCallback.filter(),
)
async def buy_ad_handler(
    callback: CallbackQuery, callback_data: BuyAdCallback, state: FSMContext
):
    ad = await MyAdsServices.get_owned_ad(callback.from_user.id, callback_data.id)
    if ad is None:
        await callback.answer(MyAdsTexts.NOT_FOUND, show_alert=True)
        return
    if ad.state == "published":
        await callback.answer(MyAdsTexts.RENEW_NOT_AVAILABLE, show_alert=True)
        return

    await _send_payment_message(
        callback,
        state,
        ad_id=callback_data.id,
        is_renewal=False,
    )


@my_ads_router.callback_query(
    StateFilter(BotFlow.my_ads, MyAds.delete_ad),
    RenewAdCallback.filter(),
)
async def renew_ad_handler(
    callback: CallbackQuery,
    callback_data: RenewAdCallback,
    state: FSMContext,
) -> None:
    ad = await MyAdsServices.get_owned_ad(callback.from_user.id, callback_data.id)
    if ad is None:
        await callback.answer(MyAdsTexts.NOT_FOUND, show_alert=True)
        return
    if ad.state != "published":
        await callback.answer(MyAdsTexts.RENEW_NOT_AVAILABLE, show_alert=True)
        return

    await _send_payment_message(
        callback,
        state,
        ad_id=callback_data.id,
        is_renewal=True,
    )


@my_ads_router.message(BotFlow.my_ads, F.text == UserMenuTexts.TO_MENU_BTN)
async def back_to_menu(message: Message, state: FSMContext) -> None:
    await MessageCleaner.track(state, message.message_id)
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
    await state.set_state(BotFlow.menu_navigation)

    notifications_amount = await notify_repo.count_unread_messages(message.from_user.id)
    title, keyboard = UserMenuViews.title(notifications_amount)
    await TitleManager.update(
        message.bot,
        message.chat.id,
        state,
        title,
        keyboard,
    )
