from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove


class TitleManager:
    """Replace the stage title and apply its reply keyboard."""

    STORAGE_KEY = "_title_message_id"

    @classmethod
    async def update(
        cls,
        bot: Bot,
        chat_id: int,
        state: FSMContext,
        text: str,
        reply_markup: InlineKeyboardMarkup
        | ReplyKeyboardMarkup
        | ReplyKeyboardRemove
        | None = None,
        parse_mode: str = "HTML",
        force_replace: bool = False,
    ) -> int:
        """Send the new title before cleaning up the previous one.

        AFK reset is the exception: it explicitly removes the stale title first.
        """
        data = await state.get_data()
        old_title_id: int | None = data.get(cls.STORAGE_KEY)

        if old_title_id and force_replace:
            await cls._delete_obsolete_title(bot, chat_id, old_title_id)

        new_msg = await bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode,
        )
        await state.update_data({cls.STORAGE_KEY: new_msg.message_id})

        if old_title_id and not force_replace:
            await cls._delete_obsolete_title(bot, chat_id, old_title_id)

        return new_msg.message_id

    @staticmethod
    async def _delete_obsolete_title(
        bot: Bot,
        chat_id: int,
        message_id: int,
    ) -> None:
        try:
            await bot.delete_message(chat_id=chat_id, message_id=message_id)
        except TelegramBadRequest:
            pass
