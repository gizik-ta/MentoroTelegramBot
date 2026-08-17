from aiogram.filters.callback_data import CallbackData


class SubjectSelectCallback(CallbackData, prefix="subject"):
    value: str


class TeachingTypeCallback(CallbackData, prefix="teaching_type"):
    value: str


class ClassesFormatCallback(CallbackData, prefix="classes_format"):
    value: str


class AdActionCallback(CallbackData, prefix="ad_action"):
    action: str  # "like", "unlike", or "contact"
    ad_id: int


class EditAdCallback(CallbackData, prefix="edit_ad"):
    """Shared contract between My Ads and the ad-making workflow."""

    id: int


class DeleteAdCallback(CallbackData, prefix="delete_ad"):
    id: int


class BuyAdCallback(CallbackData, prefix="buy_ad"):
    id: int


class RenewAdCallback(CallbackData, prefix="renew_ad"):
    id: int
