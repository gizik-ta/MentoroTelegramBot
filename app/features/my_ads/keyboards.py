from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
)
from features.common.keyboards import CommonKeyboards

from .callbacks import DefinitelyDeleteCallback
from .texts import MyAdsTexts


class MyAdsKeyboards:
    @staticmethod
    def my_ads_keyboard() -> ReplyKeyboardMarkup:
        return CommonKeyboards.owner_ads_navigation()

    @staticmethod
    def process_ads(
        ad_id: int,
        is_bought: bool,
        state: str | None = None,
    ) -> InlineKeyboardMarkup:
        return CommonKeyboards.owner_ad_actions(ad_id, is_bought, state)

    @staticmethod
    def ask_delete_ad_keyboard(ad_id: int) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=MyAdsTexts.DELETE_BUTTON,
                        callback_data=DefinitelyDeleteCallback(
                            action="delete",
                            id=ad_id,
                        ).pack(),
                    )
                ],
                [
                    InlineKeyboardButton(
                        text=MyAdsTexts.CANCEL_BUTTON,
                        callback_data=DefinitelyDeleteCallback(
                            action="back",
                            id=ad_id,
                        ).pack(),
                    )
                ],
            ]
        )

    @staticmethod
    def buy_ad_keyboard(link: str) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=MyAdsTexts.PAYMENT_BUTTON,
                        url=link,
                    )
                ]
            ]
        )
