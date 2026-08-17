from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from common.data.filters import FILTERS

from .callbacks import (
    AdActionCallback,
    FilterCallback,
    PaginationCallback,
)
from .texts import TutorSearchingTexts


class TutorSearchingKeyboards:
    @staticmethod
    def set_filters_keyboard(current_filters: list[str]) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()

        for filter_key, filter_label in FILTERS.items():
            is_active = filter_key in current_filters
            text = TutorSearchingTexts.filter_button_text(filter_label, is_active)
            action = "delete" if is_active else "set"

            builder.button(
                text=text, callback_data=FilterCallback(action=action, name=filter_key)
            )

        builder.adjust(1)
        return builder.as_markup()

    @staticmethod
    def ads_actions_keyboard(
        current_index: int, total_count: int, ad_id: int, is_liked: bool = False
    ) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()

        # Row 1: Pagination Controls
        if current_index > 0:
            builder.button(
                text=TutorSearchingTexts.BTN_PREV,
                callback_data=PaginationCallback(
                    direction="prev",
                    index=current_index,
                ),
            )
        if current_index < total_count - 1:
            builder.button(
                text=TutorSearchingTexts.BTN_NEXT,
                callback_data=PaginationCallback(
                    direction="next",
                    index=current_index,
                ),
            )

        # Row 2: Action Controls
        like_text = TutorSearchingTexts.like_button_text(is_liked)
        like_action = "unlike" if is_liked else "like"

        builder.row(
            InlineKeyboardButton(
                text=like_text,
                callback_data=AdActionCallback(
                    action=like_action,
                    ad_id=ad_id,
                ).pack(),
            ),
            InlineKeyboardButton(
                text=TutorSearchingTexts.BTN_CONTACT,
                callback_data=AdActionCallback(
                    action="contact",
                    ad_id=ad_id,
                ).pack(),
            ),
        )

        return builder.as_markup()
