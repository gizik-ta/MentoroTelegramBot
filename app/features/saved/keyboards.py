from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from features.common.callbacks import AdActionCallback
from features.common.texts import CommonTexts


class SavedAdKeyboards:
    @staticmethod
    def saved_ads_processing(ad_id: int, is_liked: bool) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()

        like_text = CommonTexts.like_button_text(is_liked)
        like_action = "unlike" if is_liked else "like"

        builder.row(
            InlineKeyboardButton(
                text=like_text,
                callback_data=AdActionCallback(
                    action=like_action,
                    ad_id=ad_id,
                ).pack(),
            ),
            InlineKeyboardButton(
                text=CommonTexts.BTN_CONTACT,
                callback_data=AdActionCallback(
                    action="contact",
                    ad_id=ad_id,
                ).pack(),
            ),
        )

        return builder.as_markup()
