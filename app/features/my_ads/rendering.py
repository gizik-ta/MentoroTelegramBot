from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardMarkup
from features.common.rendering import show_ad
from infrastructure.database import ad_repo

from .keyboards import MyAdsKeyboards
from .texts import MyAdsTexts


class MyAdsRendering:
    @staticmethod
    def title() -> tuple[str, ReplyKeyboardMarkup]:
        return (
            MyAdsTexts.TITLE,
            MyAdsKeyboards.my_ads_keyboard(),
        )

    @staticmethod
    async def description(message: Message) -> int:
        description = await message.answer(MyAdsTexts.DESCRIPTION)
        return description.message_id

    @staticmethod
    def delete_confirmation(ad_text: str, ad_id: int):
        return (
            ad_text + MyAdsTexts.DELETE_CONFIRMATION,
            MyAdsKeyboards.ask_delete_ad_keyboard(ad_id),
        )

    @staticmethod
    def restore_ad(ad_text: str, ad_id: int, is_bought: bool, state: str | None):
        return (
            ad_text.removesuffix(MyAdsTexts.DELETE_CONFIRMATION),
            MyAdsKeyboards.process_ads(ad_id, is_bought, state),
        )

    @staticmethod
    def payment(link: str, is_renewal: bool = False):
        text = (
            MyAdsTexts.RENEWAL_PAYMENT_MESSAGE
            if is_renewal
            else MyAdsTexts.PAYMENT_MESSAGE
        )
        return text, MyAdsKeyboards.buy_ad_keyboard(link)

    @staticmethod
    async def show_user_ads(
        user_id: int,
        message: Message,
        state: FSMContext,
        show_state: bool = True,
        show_statistic: bool = False,
    ):
        ads = await ad_repo.get_by_user_id(user_id)
        message_ids = []
        for ad in ads[::-1]:
            m = await show_ad(
                message,
                ad,
                MyAdsKeyboards.process_ads(ad.ad_id, ad.is_bought, ad.state),
                show_state=show_state,
                show_statistic=show_statistic,
                show_publication_end=True,
            )
            message_ids.append((ad.ad_id, m))
        return message_ids
