from aiogram.filters.callback_data import CallbackData


class PhotoActionCallback(CallbackData, prefix="ad_photo"):
    action: str


class ConfirmAdCallback(CallbackData, prefix="ad_confirm"):
    action: str
