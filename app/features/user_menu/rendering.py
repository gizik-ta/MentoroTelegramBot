from aiogram.types import ReplyKeyboardMarkup
from features.user_menu.keyboards import UserMenuKeyboards


class UserMenuViews:
    @staticmethod
    def title(notifications_amount: int) -> tuple[str, ReplyKeyboardMarkup]:
        text = "Главное меню"
        keyboard = UserMenuKeyboards.user_menu_keyboard(notifications_amount)
        return text, keyboard
