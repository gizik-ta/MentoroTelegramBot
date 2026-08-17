from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from common.utils.cleaner import MessageCleaner
from common.utils.title_manager import TitleManager
from features.common.callbacks import (
    ClassesFormatCallback,
    EditAdCallback,
    SubjectSelectCallback,
    TeachingTypeCallback,
)
from features.common.keyboards import CommonKeyboards
from features.common.rendering import show_ad
from features.common.states import BotFlow, CardMaking
from features.my_ads.states import MyAds
from infrastructure.database import ad_repo, ad_service, user_repo

from .callbacks import ConfirmAdCallback, PhotoActionCallback
from .keyboards import AdMakingKeyboards
from .rendering import AdMakingRendering
from .services import AdMakingServices
from .texts import AdMakingTexts

ad_making_router = Router()


def _edit_field_prompts() -> dict:
    return {
        AdMakingTexts.FIELD_NAME_BUTTON: (
            CardMaking.tutor_name,
            AdMakingTexts.EDIT_NAME_PROMPT,
            None,
        ),
        AdMakingTexts.FIELD_PHOTO_BUTTON: (
            CardMaking.tutor_photo,
            AdMakingTexts.EDIT_PHOTO_PROMPT,
            None,
        ),
        AdMakingTexts.FIELD_SUBJECT_BUTTON: (
            CardMaking.tutor_subject,
            AdMakingTexts.EDIT_SUBJECT_PROMPT,
            CommonKeyboards.choose_subject_keyboard(),
        ),
        AdMakingTexts.FIELD_DIRECTION_BUTTON: (
            CardMaking.tutor_teaching_type,
            AdMakingTexts.EDIT_DIRECTION_PROMPT,
            CommonKeyboards.choose_teaching_type(),
        ),
        AdMakingTexts.FIELD_EXPERIENCE_BUTTON: (
            CardMaking.tutor_experience,
            AdMakingTexts.EDIT_EXPERIENCE_PROMPT,
            None,
        ),
        AdMakingTexts.FIELD_FORMAT_BUTTON: (
            CardMaking.tutor_classes_format,
            AdMakingTexts.EDIT_FORMAT_PROMPT,
            CommonKeyboards.choose_classes_format(),
        ),
        AdMakingTexts.FIELD_PRICE_BUTTON: (
            CardMaking.tutor_price,
            AdMakingTexts.EDIT_PRICE_PROMPT,
            None,
        ),
        AdMakingTexts.FIELD_DESCRIPTION_BUTTON: (
            CardMaking.tutor_description,
            AdMakingTexts.EDIT_DESCRIPTION_PROMPT,
            None,
        ),
    }


async def _send_prompt(
    target: Message,
    state: FSMContext,
    text: str,
    reply_markup=None,
    parse_mode: str | None = None,
) -> Message:
    """Replace the previous question, answer, and validation messages."""

    await MessageCleaner.purge(target.bot, target.chat.id, state)
    prompt = await target.answer(
        text,
        reply_markup=reply_markup,
        parse_mode=parse_mode,
    )
    await MessageCleaner.track(state, prompt.message_id)
    return prompt


async def _send_validation_error(
    target: Message,
    state: FSMContext,
    text: str,
) -> Message:
    """Show an existing validation message without clearing the current step."""

    error = await target.answer(text)
    await MessageCleaner.track(state, error.message_id)
    return error


async def _send_photo_status(
    target: Message,
    state: FSMContext,
    photos: list[str],
    is_changing: bool,
    error_text: str | None = None,
) -> None:
    if error_text:
        error = await target.answer(error_text)
        await MessageCleaner.track(state, error.message_id)
    status = await target.answer(
        AdMakingTexts.photo_count(len(photos)),
        reply_markup=AdMakingKeyboards.add_photo_keyboard(photos, is_changing),
    )
    await MessageCleaner.track(state, status.message_id)


async def _show_confirmation(target: Message, state: FSMContext) -> None:
    await MessageCleaner.purge(target.bot, target.chat.id, state)
    message_ids = await AdMakingRendering.show_ad_confirm(
        target,
        state,
        show_edit_keyboard=True,
    )
    await MessageCleaner.track(state, message_ids)


async def _show_owner_ads(target: Message, state: FSMContext, user_id: int) -> None:
    ads = await ad_repo.get_by_user_id(user_id)
    for ad in ads[::-1]:
        message_ids = await show_ad(
            target,
            ad,
            CommonKeyboards.owner_ad_actions(ad.ad_id, ad.is_bought, ad.state),
            show_state=True,
            show_statistic=False,
            show_publication_end=True,
        )
        await state.update_data(**{f"ad_{ad.ad_id}": message_ids})
        await MessageCleaner.track(state, message_ids)


async def _reset_to_my_ads(
    target: Message,
    state: FSMContext,
    user_id: int,
) -> None:
    await MessageCleaner.purge(target.bot, target.chat.id, state)
    await MessageCleaner.clear_state_preserving(
        state,
        TitleManager.STORAGE_KEY,
        MessageCleaner.GREETING_STORAGE_KEY,
    )
    await state.set_state(BotFlow.my_ads)

    await TitleManager.update(
        target.bot,
        target.chat.id,
        state,
        AdMakingTexts.OWNER_ADS_TITLE,
        CommonKeyboards.owner_ads_navigation(),
    )

    description = await target.answer(AdMakingTexts.OWNER_ADS_DESCRIPTION)
    await MessageCleaner.track(state, description.message_id)

    await _show_owner_ads(target, state, user_id)


@ad_making_router.message(
    BotFlow.my_ads,
    F.text == AdMakingTexts.CREATE_BUTTON,
)
async def create_ad_handler(message: Message, state: FSMContext) -> None:
    await MessageCleaner.track(state, message.message_id)
    await MessageCleaner.purge(message.bot, message.chat.id, state)
    await MessageCleaner.clear_state_preserving(
        state,
        TitleManager.STORAGE_KEY,
        MessageCleaner.GREETING_STORAGE_KEY,
    )

    await state.set_state(CardMaking.tutor_name)
    await state.update_data(update_ad=False, ad_id=None, is_changing=False)
    await TitleManager.update(
        message.bot,
        message.chat.id,
        state,
        AdMakingTexts.CREATE_TITLE,
        AdMakingKeyboards.making_ad_keyboard(),
    )

    prompt = await message.answer(
        AdMakingTexts.NAME_PROMPT,
    )
    await MessageCleaner.track(state, prompt.message_id)


@ad_making_router.callback_query(
    StateFilter(BotFlow.my_ads, MyAds.delete_ad),
    EditAdCallback.filter(),
)
async def edit_ad_handler(
    callback: CallbackQuery,
    callback_data: EditAdCallback,
    state: FSMContext,
) -> None:
    ad = await ad_repo.get_by_id(callback_data.id)
    if ad is None or ad.user_id != callback.from_user.id:
        await callback.answer(AdMakingTexts.NOT_FOUND, show_alert=True)
        return

    await MessageCleaner.delete_key_messages(
        callback.message.bot,
        callback.message.chat.id,
        state,
        MessageCleaner.PAYMENT_STORAGE_KEY,
    )
    await MessageCleaner.purge(callback.message.bot, callback.message.chat.id, state)
    await MessageCleaner.clear_state_preserving(
        state,
        TitleManager.STORAGE_KEY,
        MessageCleaner.GREETING_STORAGE_KEY,
    )
    await state.update_data(**AdMakingServices.edit_data(ad))
    await state.set_state(CardMaking.tutor_confirm)

    await TitleManager.update(
        callback.message.bot,
        callback.message.chat.id,
        state,
        AdMakingTexts.EDIT_TITLE,
    )
    await _show_confirmation(callback.message, state)
    await callback.answer()


@ad_making_router.callback_query(
    StateFilter(CardMaking),
    ConfirmAdCallback.filter(F.action == "cancel"),
)
async def cancel_ad(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    cancellation_text = (
        AdMakingTexts.EDITING_CANCELLED
        if data.get("update_ad")
        else AdMakingTexts.CREATION_CANCELLED
    )
    await callback.answer(cancellation_text)
    await _reset_to_my_ads(
        callback.message,
        state,
        callback.from_user.id,
    )


@ad_making_router.message(
    StateFilter(CardMaking),
    F.text == AdMakingTexts.CANCEL_BUTTON,
)
async def cancel_ad_creation(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    if data.get("update_ad"):
        return
    await _reset_to_my_ads(message, state, message.from_user.id)


@ad_making_router.message(CardMaking.tutor_name)
async def ad_tutor_name(message: Message, state: FSMContext) -> None:
    await MessageCleaner.track(state, message.message_id)
    name = message.text.strip().split() if message.text else []
    if len(name) != 3:
        await _send_validation_error(message, state, AdMakingTexts.NAME_INVALID)
        return

    await state.update_data(
        tutor_name=name,
        tutor_username=message.from_user.username,
    )
    if (await state.get_data()).get("is_changing"):
        await _show_confirmation(message, state)
        return

    await state.set_state(CardMaking.tutor_photo)
    await _send_prompt(
        message,
        state,
        AdMakingTexts.PHOTO_PROMPT,
        parse_mode="HTML",
    )


@ad_making_router.message(
    StateFilter(CardMaking.tutor_photo, CardMaking.tutor_photo_confirm),
    F.photo,
)
async def ad_tutor_photo(message: Message, state: FSMContext) -> None:
    await MessageCleaner.track(state, message.message_id)
    data = await state.get_data()
    photos = list(data.get("tutor_photo") or [])
    is_changing = data.get("is_changing", False)
    current_state = await state.get_state()

    if message.media_group_id:
        if data.get("processed_media_group_id") == message.media_group_id:
            await MessageCleaner.delete_message(
                message.bot,
                message.chat.id,
                state,
                message.message_id,
            )
            return

        if len(photos) < 6:
            photos.append(message.photo[-1].file_id)
            await state.update_data(tutor_photo=photos)
        await state.update_data(processed_media_group_id=message.media_group_id)
        await state.set_state(CardMaking.tutor_photo_confirm)
        await _send_photo_status(
            message,
            state,
            photos,
            is_changing,
            AdMakingTexts.PHOTO_ONE_BY_ONE,
        )
        return

    if current_state == CardMaking.tutor_photo_confirm.state:
        await _send_photo_status(message, state, photos, is_changing)
        return

    if len(photos) >= 6:
        await state.set_state(CardMaking.tutor_photo_confirm)
        await _send_photo_status(
            message,
            state,
            photos,
            is_changing,
            AdMakingTexts.PHOTO_MAXIMUM,
        )
        return

    photos.append(message.photo[-1].file_id)
    await state.update_data(tutor_photo=photos)
    await state.set_state(CardMaking.tutor_photo_confirm)
    await _send_photo_status(message, state, photos, is_changing)


@ad_making_router.callback_query(
    CardMaking.tutor_photo_confirm,
    PhotoActionCallback.filter(),
)
async def process_photo(
    callback: CallbackQuery,
    callback_data: PhotoActionCallback,
    state: FSMContext,
) -> None:
    action = callback_data.action
    data = await state.get_data()
    photos = list(data.get("tutor_photo") or [])

    if action == "choose_again":
        await state.update_data(tutor_photo=[])
        await state.set_state(CardMaking.tutor_photo)
        await _send_prompt(callback.message, state, AdMakingTexts.PHOTO_REUPLOAD)
    elif action == "next_question":
        await state.set_state(CardMaking.tutor_subject)
        await _send_prompt(
            callback.message,
            state,
            AdMakingTexts.SUBJECT_PROMPT,
            CommonKeyboards.choose_subject_keyboard(),
            "HTML",
        )
    elif action == "add_photo":
        await state.set_state(CardMaking.tutor_photo)
        await _send_prompt(callback.message, state, AdMakingTexts.PHOTO_NEXT)
    elif action == "save_changing_photo":
        await _show_confirmation(callback.message, state)
    else:
        await _send_photo_status(
            callback.message,
            state,
            photos,
            data.get("is_changing", False),
        )
    await callback.answer()


@ad_making_router.callback_query(
    CardMaking.tutor_subject,
    SubjectSelectCallback.filter(),
)
async def ad_subject(
    callback: CallbackQuery,
    callback_data: SubjectSelectCallback,
    state: FSMContext,
) -> None:
    await state.update_data(tutor_subject=callback_data.value)
    if (await state.get_data()).get("is_changing"):
        await _show_confirmation(callback.message, state)
    else:
        await state.set_state(CardMaking.tutor_teaching_type)
        await _send_prompt(
            callback.message,
            state,
            AdMakingTexts.TEACHING_TYPE_PROMPT,
            CommonKeyboards.choose_teaching_type(),
            "HTML",
        )
    await callback.answer()


@ad_making_router.callback_query(
    CardMaking.tutor_teaching_type,
    TeachingTypeCallback.filter(),
)
async def ad_teaching_type(
    callback: CallbackQuery,
    callback_data: TeachingTypeCallback,
    state: FSMContext,
) -> None:
    await state.update_data(tutor_teaching_type=callback_data.value)
    if (await state.get_data()).get("is_changing"):
        await _show_confirmation(callback.message, state)
    else:
        await state.set_state(CardMaking.tutor_experience)
        await _send_prompt(
            callback.message,
            state,
            AdMakingTexts.EXPERIENCE_PROMPT,
            parse_mode="HTML",
        )
    await callback.answer()


@ad_making_router.message(CardMaking.tutor_experience)
async def ad_experience(message: Message, state: FSMContext) -> None:
    await MessageCleaner.track(state, message.message_id)
    text = message.text.strip() if message.text else ""
    if len(text) < 20:
        await _send_validation_error(
            message,
            state,
            AdMakingTexts.EXPERIENCE_INVALID,
        )
        return

    await state.update_data(tutor_experience=text)
    if (await state.get_data()).get("is_changing"):
        await _show_confirmation(message, state)
        return

    await state.set_state(CardMaking.tutor_classes_format)
    await _send_prompt(
        message,
        state,
        AdMakingTexts.CLASSES_FORMAT_PROMPT,
        CommonKeyboards.choose_classes_format(),
    )


@ad_making_router.callback_query(
    CardMaking.tutor_classes_format,
    ClassesFormatCallback.filter(),
)
async def ad_classes_format(
    callback: CallbackQuery,
    callback_data: ClassesFormatCallback,
    state: FSMContext,
) -> None:
    await state.update_data(tutor_classes_format=callback_data.value)
    if (await state.get_data()).get("is_changing"):
        await _show_confirmation(callback.message, state)
    else:
        await state.set_state(CardMaking.tutor_price)
        await _send_prompt(callback.message, state, AdMakingTexts.PRICE_PROMPT)
    await callback.answer()


@ad_making_router.message(CardMaking.tutor_price)
async def ad_price(message: Message, state: FSMContext) -> None:
    await MessageCleaner.track(state, message.message_id)
    try:
        price = int(message.text.strip()) if message.text else 0
    except ValueError:
        await _send_validation_error(message, state, AdMakingTexts.PRICE_INVALID)
        return

    if price <= 0:
        await _send_validation_error(message, state, AdMakingTexts.PRICE_INVALID)
        return
    if price > 2_000_000_000:
        await _send_validation_error(message, state, AdMakingTexts.PRICE_TOO_LARGE)
        return

    await state.update_data(tutor_price=price)
    if (await state.get_data()).get("is_changing"):
        await _show_confirmation(message, state)
        return

    await state.set_state(CardMaking.tutor_description)
    await _send_prompt(
        message,
        state,
        AdMakingTexts.DESCRIPTION_PROMPT,
        parse_mode="HTML",
    )


@ad_making_router.message(CardMaking.tutor_description)
async def ad_description(message: Message, state: FSMContext) -> None:
    await MessageCleaner.track(state, message.message_id)
    text = message.text.strip() if message.text else ""
    if len(text) < 50:
        await _send_validation_error(
            message,
            state,
            AdMakingTexts.DESCRIPTION_INVALID,
        )
        return

    await state.update_data(tutor_description=text)
    await _show_confirmation(message, state)


@ad_making_router.message(CardMaking.tutor_confirm)
async def ad_change_input(message: Message, state: FSMContext) -> None:
    await MessageCleaner.track(state, message.message_id)
    prompt = _edit_field_prompts().get(message.text or "")
    if prompt is None:
        await _show_confirmation(message, state)
        return

    await state.update_data(is_changing=True)
    next_state, text, keyboard = prompt
    if message.text == AdMakingTexts.FIELD_PHOTO_BUTTON:
        await state.update_data(tutor_photo=[])
    await state.set_state(next_state)
    await _send_prompt(message, state, text, keyboard)


@ad_making_router.callback_query(
    CardMaking.tutor_confirm,
    ConfirmAdCallback.filter(),
)
async def ad_confirm(
    callback: CallbackQuery,
    callback_data: ConfirmAdCallback,
    state: FSMContext,
) -> None:
    if callback_data.action != "confirm":
        await callback.answer()
        return

    data = await state.get_data()

    if data.get("update_ad") and not AdMakingServices.has_information_changes(data):
        await callback.answer(AdMakingTexts.EDITING_COMPLETED)
        await _reset_to_my_ads(
            callback.message,
            state,
            callback.from_user.id,
        )
        return

    ad = AdMakingServices.build_ad(data)
    await user_repo.add_user(callback.from_user.id)

    if data.get("update_ad"):
        ad = AdMakingServices.prepare_updated_ad(ad)
        saved = await ad_repo.update_ad(ad.ad_id, callback.from_user.id, ad)
        if not saved:
            await callback.answer(AdMakingTexts.NOT_FOUND, show_alert=True)
            return
        completion_text = (
            AdMakingTexts.UPDATED_PENDING_REVIEW
            if ad.state == "on_check"
            else AdMakingTexts.UPDATED_PENDING_PAYMENT
        )
    else:
        await ad_service.create_ad(callback.from_user.id, ad)
        completion_text = AdMakingTexts.CREATED

    await callback.answer(completion_text)
    await _reset_to_my_ads(
        callback.message,
        state,
        callback.from_user.id,
    )


@ad_making_router.message(StateFilter(CardMaking))
async def clean_irrelevant_message(message: Message) -> None:
    """Ignore irrelevant input; global tracking clears it on the next transition."""
