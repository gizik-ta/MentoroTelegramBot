from aiogram.types import KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, ReplyKeyboardMarkup

from .texts import UserMenuTexts


class UserMenuKeyboards:
    @staticmethod
    def user_menu_keyboard(notifications_amount: int = 0) -> ReplyKeyboardMarkup:
        builder = ReplyKeyboardBuilder()

        notif_text = UserMenuTexts.NOTIFICATIONS_BTN
        if notifications_amount > 0:
            notif_text += f" ({notifications_amount} 📥)"

        builder.row(
            KeyboardButton(text=UserMenuTexts.TUTOR_SEARCH_BTN),
            KeyboardButton(text=notif_text),
        )
        builder.row(
            KeyboardButton(text=UserMenuTexts.MY_ADS_BTN),
            KeyboardButton(text=UserMenuTexts.SAVED_ADS_BTN),
        )

        return builder.as_markup(resize_keyboard=True)

    @staticmethod
    def back_to_menu_keyboard() -> ReplyKeyboardMarkup:
        builder = ReplyKeyboardBuilder()
        builder.row(KeyboardButton(text=UserMenuTexts.TO_MENU_BTN))
        return builder.as_markup(resize_keyboard=True)
