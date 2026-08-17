from aiogram.filters.callback_data import CallbackData
from features.common.callbacks import AdActionCallback

__all__ = ["AdActionCallback", "FilterCallback", "PaginationCallback"]


class FilterCallback(CallbackData, prefix="filter"):
    action: str  # "set" or "delete"
    name: str


class PaginationCallback(CallbackData, prefix="feed_shift"):
    direction: str  # "next" or "prev"
    index: int
