from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from aiogram.utils.keyboard import ReplyKeyboardBuilder

from .callbacks import ModerationCallback, RejectionCallback
from .texts import AdminTexts


class AdminKeyboards:
    @staticmethod
    def menu() -> ReplyKeyboardMarkup:
        builder = ReplyKeyboardBuilder()
        builder.row(
            KeyboardButton(text=AdminTexts.CHECK_ADS_BUTTON),
            KeyboardButton(text=AdminTexts.STATISTICS_BUTTON),
        )
        builder.row(KeyboardButton(text=AdminTexts.NOTIFICATIONS_BUTTON))
        return builder.as_markup(resize_keyboard=True)

    @staticmethod
    def moderation_navigation() -> ReplyKeyboardMarkup:
        builder = ReplyKeyboardBuilder()
        builder.row(KeyboardButton(text=AdminTexts.BACK_TO_MENU_BUTTON))
        return builder.as_markup(resize_keyboard=True)

    @staticmethod
    def moderation_actions(ad_id: int) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=AdminTexts.APPROVE_BUTTON,
                        callback_data=ModerationCallback(
                            action="approve",
                            ad_id=ad_id,
                        ).pack(),
                    ),
                    InlineKeyboardButton(
                        text=AdminTexts.REJECT_BUTTON,
                        callback_data=ModerationCallback(
                            action="reject",
                            ad_id=ad_id,
                        ).pack(),
                    ),
                ]
            ]
        )

    @staticmethod
    def rejection_actions(ad_id: int) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=AdminTexts.CANCEL_BUTTON,
                        callback_data=RejectionCallback(
                            action="cancel",
                            ad_id=ad_id,
                        ).pack(),
                    ),
                    InlineKeyboardButton(
                        text=AdminTexts.CONFIRM_REJECTION_BUTTON,
                        callback_data=RejectionCallback(
                            action="confirm",
                            ad_id=ad_id,
                        ).pack(),
                    ),
                ]
            ]
        )
