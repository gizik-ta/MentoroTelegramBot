from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from aiogram.utils.keyboard import ReplyKeyboardBuilder

from .callbacks import ConfirmAdCallback, PhotoActionCallback
from .texts import AdMakingTexts


class AdMakingKeyboards:
    @staticmethod
    def making_ad_keyboard() -> ReplyKeyboardMarkup:
        builder = ReplyKeyboardBuilder()
        builder.row(KeyboardButton(text=AdMakingTexts.CANCEL_BUTTON))
        return builder.as_markup(resize_keyboard=True)

    @staticmethod
    def add_photo_keyboard(
        photos: list[str],
        is_changing: bool,
    ) -> InlineKeyboardMarkup:
        if is_changing:
            confirm_text = AdMakingTexts.PHOTO_SAVE_BUTTON
            confirm_action = "save_changing_photo"
        else:
            confirm_text = AdMakingTexts.NEXT_QUESTION_BUTTON
            confirm_action = "next_question"

        rows = []
        if len(photos) < 6:
            rows.append(
                [
                    InlineKeyboardButton(
                        text=AdMakingTexts.ADD_PHOTO_BUTTON,
                        callback_data=PhotoActionCallback(action="add_photo").pack(),
                    )
                ]
            )
        rows.append(
            [
                InlineKeyboardButton(
                    text=AdMakingTexts.RESELECT_PHOTO_BUTTON,
                    callback_data=PhotoActionCallback(action="choose_again").pack(),
                ),
                InlineKeyboardButton(
                    text=confirm_text,
                    callback_data=PhotoActionCallback(action=confirm_action).pack(),
                ),
            ]
        )
        return InlineKeyboardMarkup(inline_keyboard=rows)

    @staticmethod
    def change_input() -> ReplyKeyboardMarkup:
        builder = ReplyKeyboardBuilder()
        builder.row(
            KeyboardButton(text=AdMakingTexts.FIELD_NAME_BUTTON),
            KeyboardButton(text=AdMakingTexts.FIELD_PHOTO_BUTTON),
        )
        builder.row(
            KeyboardButton(text=AdMakingTexts.FIELD_SUBJECT_BUTTON),
            KeyboardButton(text=AdMakingTexts.FIELD_DIRECTION_BUTTON),
        )
        builder.row(
            KeyboardButton(text=AdMakingTexts.FIELD_EXPERIENCE_BUTTON),
            KeyboardButton(text=AdMakingTexts.FIELD_FORMAT_BUTTON),
        )
        builder.row(
            KeyboardButton(text=AdMakingTexts.FIELD_PRICE_BUTTON),
            KeyboardButton(text=AdMakingTexts.FIELD_DESCRIPTION_BUTTON),
        )
        return builder.as_markup(resize_keyboard=True)

    @staticmethod
    def confirm_ad(is_editing: bool = False) -> InlineKeyboardMarkup:
        cancel_text = (
            AdMakingTexts.CANCEL_EDITING_BUTTON
            if is_editing
            else AdMakingTexts.CANCEL_BUTTON
        )
        first_row = [
            InlineKeyboardButton(
                text=cancel_text,
                callback_data=ConfirmAdCallback(action="cancel").pack(),
            )
        ]
        first_row.append(
            InlineKeyboardButton(
                text=AdMakingTexts.CONFIRM_BUTTON,
                callback_data=ConfirmAdCallback(action="confirm").pack(),
            )
        )
        return InlineKeyboardMarkup(inline_keyboard=[first_row])
