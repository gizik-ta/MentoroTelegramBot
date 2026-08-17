from aiogram.filters.callback_data import CallbackData
from features.common.callbacks import (
    BuyAdCallback,
    DeleteAdCallback,
    EditAdCallback,
    RenewAdCallback,
)

__all__ = [
    "BuyAdCallback",
    "DefinitelyDeleteCallback",
    "DeleteAdCallback",
    "EditAdCallback",
    "RenewAdCallback",
]


class DefinitelyDeleteCallback(CallbackData, prefix="ask_delete_ad"):
    action: str  # delete, back
    id: int
