from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from .callbacks import (
    BuyAdCallback,
    ClassesFormatCallback,
    DeleteAdCallback,
    EditAdCallback,
    RenewAdCallback,
    SubjectSelectCallback,
    TeachingTypeCallback,
)
from .texts import CommonTexts


class CommonKeyboards:
    @staticmethod
    def owner_ads_navigation() -> ReplyKeyboardMarkup:
        """Shared boundary keyboard used by My Ads and ad-making completion."""

        builder = ReplyKeyboardBuilder()
        builder.row(
            KeyboardButton(text=CommonTexts.CREATE_AD_BUTTON),
            KeyboardButton(text=CommonTexts.BACK_TO_MENU_BUTTON),
        )
        return builder.as_markup(resize_keyboard=True)

    @staticmethod
    def owner_ad_actions(
        ad_id: int,
        is_bought: bool,
        state: str | None = None,
    ) -> InlineKeyboardMarkup:
        actions = []
        if state == "published":
            actions.append(
                [
                    InlineKeyboardButton(
                        text=CommonTexts.RENEW_AD_BUTTON,
                        callback_data=RenewAdCallback(id=ad_id).pack(),
                    )
                ]
            )
        if not is_bought:
            actions.append(
                [
                    InlineKeyboardButton(
                        text=CommonTexts.BUY_AD_BUTTON,
                        callback_data=BuyAdCallback(id=ad_id).pack(),
                    )
                ]
            )
        actions.append(
            [
                InlineKeyboardButton(
                    text=CommonTexts.DELETE_AD_BUTTON,
                    callback_data=DeleteAdCallback(id=ad_id).pack(),
                ),
                InlineKeyboardButton(
                    text=CommonTexts.EDIT_AD_BUTTON,
                    callback_data=EditAdCallback(id=ad_id).pack(),
                ),
            ]
        )
        return InlineKeyboardMarkup(inline_keyboard=actions)

    @staticmethod
    def choose_subject_keyboard() -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()

        for callback_key, label in CommonTexts.SUBJECTS.items():
            builder.button(
                text=label,
                callback_data=SubjectSelectCallback(value=callback_key),
            )

        builder.adjust(3)
        return builder.as_markup()

    @staticmethod
    def choose_teaching_type() -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()

        for callback_key, label in CommonTexts.TEACHING_TYPES.items():
            builder.button(
                text=label,
                callback_data=TeachingTypeCallback(value=callback_key),
            )

        builder.adjust(1)
        return builder.as_markup()

    @staticmethod
    def choose_classes_format() -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()

        for callback_key, label in CommonTexts.CLASSES_FORMATS.items():
            builder.button(
                text=label,
                callback_data=ClassesFormatCallback(value=callback_key),
            )

        builder.adjust(2, 1)
        return builder.as_markup()
