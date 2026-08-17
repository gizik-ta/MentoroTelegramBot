from aiogram.filters.callback_data import CallbackData


class DeleteNotificationCallback(CallbackData, prefix="delete_notification"):
    id: int
