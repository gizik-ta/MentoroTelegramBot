from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from .callbacks import DeleteNotificationCallback
from .texts import NotificationsTexts


class NotificationsKeyboards:
    @staticmethod
    def delete_notification(notification_id: int) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()

        builder.row(
            InlineKeyboardButton(
                text=NotificationsTexts.DELETE_MESSAGE_BTN,
                callback_data=DeleteNotificationCallback(id=notification_id).pack(),
            )
        )

        return builder.as_markup()
