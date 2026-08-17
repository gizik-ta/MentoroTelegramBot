from aiogram.types import Message, ReplyKeyboardMarkup
from features.common.rendering import show_ad
from features.user_menu.keyboards import UserMenuKeyboards

from .keyboards import SavedAdKeyboards
from .texts import SavedTexts


class SavedViews:
    @staticmethod
    def title() -> tuple[str, ReplyKeyboardMarkup]:
        text = SavedTexts.TITLE
        keyboard = UserMenuKeyboards.back_to_menu_keyboard()

        return text, keyboard

    @staticmethod
    async def show_ads(message: Message, ads) -> list[int]:
        if not ads:
            empty = await message.answer(SavedTexts.EMPTY_SAVED_MESSAGE)
            return [empty.message_id]

        message_ids = []
        for ad in ads:
            rendered = await show_ad(
                message,
                ad,
                SavedAdKeyboards.saved_ads_processing(ad.ad_id, is_liked=True),
                show_state=False,
                show_statistic=False,
            )
            message_ids.extend(rendered)
        return message_ids
