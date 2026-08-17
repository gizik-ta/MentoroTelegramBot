from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.types import InputMediaPhoto, Message
from features.common.rendering import TEXT_LIMIT, render_message
from features.common.states import CardMaking
from features.common.texts import CommonTexts

from .keyboards import AdMakingKeyboards
from .services import AdMakingServices


class AdMakingRendering:
    @staticmethod
    async def show_ad_confirm(
        target: Message,
        state: FSMContext,
        show_edit_keyboard: bool = False,
    ) -> list[int]:
        data = await state.get_data()
        ad = AdMakingServices.build_ad(data)
        photos = data.get("tutor_photo") or []

        await state.set_state(CardMaking.tutor_confirm)
        await state.update_data(is_changing=False)

        ad_text = render_message(ad)
        full_html = CommonTexts.CONFIRM_AD_PROMPT.format(ad_text=ad_text)
        sent_message_ids = []

        if photos:
            photo_messages = await target.answer_media_group(
                media=[InputMediaPhoto(media=photo) for photo in photos],
            )
            sent_message_ids.extend(message.message_id for message in photo_messages)

        text = (
            full_html
            if len(full_html) <= TEXT_LIMIT
            else full_html[: TEXT_LIMIT - 3] + "..."
        )
        confirmation = await target.answer(
            text,
            reply_markup=AdMakingKeyboards.confirm_ad(
                is_editing=bool(data.get("update_ad"))
            ),
            parse_mode=ParseMode.HTML,
        )
        sent_message_ids.append(confirmation.message_id)

        if show_edit_keyboard:
            edit_message = await target.answer(
                CommonTexts.EDIT_FIELDS_PROMPT,
                reply_markup=AdMakingKeyboards.change_input(),
            )
            sent_message_ids.append(edit_message.message_id)

        return sent_message_ids
