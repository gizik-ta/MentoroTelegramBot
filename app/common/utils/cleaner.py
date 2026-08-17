import logging

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext

logger = logging.getLogger(__name__)


class MessageCleaner:
    """Utility class to track and delete temporary UI messages."""

    STORAGE_KEY = "_tracked_message_ids"
    PAYMENT_STORAGE_KEY = "_payment_message_ids"
    GREETING_STORAGE_KEY = "_greeting_message_id"

    @classmethod
    async def track(cls, state: FSMContext, message_id: int | list[int]) -> None:
        """Add a message ID to the tracking list in FSM state."""
        data = await state.get_data()
        tracked = data.get(cls.STORAGE_KEY, [])
        new_ids = message_id if isinstance(message_id, list) else [message_id]
        tracked.extend(msg_id for msg_id in new_ids if msg_id not in tracked)
        await state.update_data(**{cls.STORAGE_KEY: tracked})

    @classmethod
    async def untrack(cls, state: FSMContext, message_id: int | list[int]) -> None:
        data = await state.get_data()
        tracked = data.get(cls.STORAGE_KEY, [])
        removed = set(message_id if isinstance(message_id, list) else [message_id])
        await state.update_data(
            **{cls.STORAGE_KEY: [msg_id for msg_id in tracked if msg_id not in removed]}
        )

    @staticmethod
    async def clear_state_preserving(
        state: FSMContext,
        *storage_keys: str,
    ) -> None:
        data = await state.get_data()
        preserved = {
            key: data[key] for key in storage_keys if data.get(key) is not None
        }
        await state.clear()
        if preserved:
            await state.update_data(**preserved)

    @classmethod
    async def track_in_key(
        cls,
        state: FSMContext,
        storage_key: str,
        message_id: int | list[int],
    ) -> None:
        data = await state.get_data()
        tracked = data.get(storage_key, [])
        new_ids = message_id if isinstance(message_id, list) else [message_id]
        tracked.extend(msg_id for msg_id in new_ids if msg_id not in tracked)
        await state.update_data(**{storage_key: tracked})

    @classmethod
    async def delete_key_messages(
        cls,
        bot: Bot,
        chat_id: int,
        state: FSMContext,
        storage_key: str,
    ) -> None:
        data = await state.get_data()
        message_ids: list[int] = data.get(storage_key, [])
        if not message_ids:
            return

        await cls.delete_message(bot, chat_id, state, message_ids)
        await state.update_data(**{storage_key: []})

    @classmethod
    async def purge(cls, bot: Bot, chat_id: int, state: FSMContext) -> None:
        """Delete tracked temporary prompts and intermediate user inputs."""
        data = await state.get_data()
        message_ids: list[int] = data.get(cls.STORAGE_KEY, [])
        help_msgs: list[int] = data.get("help_messages", [])
        payment_msgs: list[int] = data.get(cls.PAYMENT_STORAGE_KEY, [])

        all_to_delete = list(dict.fromkeys(message_ids + help_msgs + payment_msgs))

        if not all_to_delete:
            return

        await cls._best_effort_delete(bot, chat_id, all_to_delete)

        await state.update_data(
            **{
                cls.STORAGE_KEY: [],
                "help_messages": [],
                cls.PAYMENT_STORAGE_KEY: [],
            }
        )

    @classmethod
    async def delete_message(
        cls,
        bot: Bot,
        chat_id: int,
        state: FSMContext,
        message_id: int | list[int],
    ) -> None:
        """Delete a certain group of messages"""
        if not message_id:
            logger.debug(
                "Empty message list in chat %s on state %s",
                chat_id,
                await state.get_state(),
            )
            return

        message_ids = message_id if isinstance(message_id, list) else [message_id]
        await cls._best_effort_delete(bot, chat_id, message_ids)
        await cls.untrack(state, message_ids)

    @classmethod
    async def clear_all_state_messages(
        cls, bot: Bot, chat_id: int, state: FSMContext
    ) -> None:
        """Delete messages accumulated before shifting to the main menu."""
        data = await state.get_data()

        tracked_ids: list[int] = data.get(cls.STORAGE_KEY, [])
        help_ids: list[int] = data.get("help_messages", [])
        payment_ids: list[int] = data.get(cls.PAYMENT_STORAGE_KEY, [])
        scroll_ids: list[int] = data.get("ads_scrolling_message_id", [])
        main_msg_id = data.get("main_message_id")

        to_delete = list(
            dict.fromkeys(tracked_ids + help_ids + payment_ids + scroll_ids)
        )
        if main_msg_id:
            to_delete.append(main_msg_id)

        if not to_delete:
            return

        await cls._best_effort_delete(bot, chat_id, to_delete)

        await state.update_data(
            **{
                cls.STORAGE_KEY: [],
                "help_messages": [],
                cls.PAYMENT_STORAGE_KEY: [],
                "ads_scrolling_message_id": [],
                "main_message_id": None,
            }
        )

    @staticmethod
    async def _best_effort_delete(
        bot: Bot,
        chat_id: int,
        message_ids: list[int],
    ) -> None:
        unique_ids = list(dict.fromkeys(message_ids))
        for offset in range(0, len(unique_ids), 100):
            batch = unique_ids[offset : offset + 100]
            try:
                if len(batch) == 1:
                    await bot.delete_message(chat_id=chat_id, message_id=batch[0])
                else:
                    await bot.delete_messages(chat_id=chat_id, message_ids=batch)
            except TelegramAPIError:
                for msg_id in batch:
                    try:
                        await bot.delete_message(chat_id=chat_id, message_id=msg_id)
                    except TelegramAPIError:
                        pass
