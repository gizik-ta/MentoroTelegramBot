from aiogram.types import InlineKeyboardMarkup, ReplyKeyboardMarkup
from features.user_menu.keyboards import UserMenuKeyboards

from .keyboards import NotificationsKeyboards
from .models import Notification
from .texts import NotificationsTexts


class NotificationsViews:
    @staticmethod
    def title() -> tuple[str, ReplyKeyboardMarkup]:
        text = NotificationsTexts.TITLE
        keyboard = UserMenuKeyboards.back_to_menu_keyboard()

        return text, keyboard

    @staticmethod
    def notification_view(
        notification: Notification,
    ) -> tuple[str, InlineKeyboardMarkup]:
        if notification.is_read:
            text = notification.notification_text
        else:
            text = (
                NotificationsTexts.NEW_MESSAGE_PREFIX + notification.notification_text
            )

        keyboard = NotificationsKeyboards.delete_notification(
            notification.notification_id
        )

        return text, keyboard
