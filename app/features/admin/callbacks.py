from aiogram.filters.callback_data import CallbackData


class ModerationCallback(CallbackData, prefix="moderate_ad"):
    action: str  # approve, reject
    ad_id: int


class RejectionCallback(CallbackData, prefix="reject_ad"):
    action: str  # cancel, confirm
    ad_id: int
