import logging
from typing import ClassVar

from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State
from aiogram.types import CallbackQuery, InputMediaPhoto, Message
from common.utils.cleaner import MessageCleaner
from features.common.rendering import render_message
from features.tutor_searching.keyboards import TutorSearchingKeyboards
from features.tutor_searching.rendering import TutorSearchingViews
from features.tutor_searching.states import TutorSearch
from features.tutor_searching.texts import TutorSearchingTexts
from infrastructure.database import ad_repo

logger = logging.getLogger(__name__)


class FeedService:
    """Orchestrates ad rendering, pagination display, and media cleanup."""

    FILTER_STATES: ClassVar[dict[str, State]] = {
        "price": TutorSearch.price_filter,
        "classes_format": TutorSearch.classes_format_filter,
        "teaching_type": TutorSearch.teaching_type_filter,
    }

    @classmethod
    async def select_subject(
        cls,
        event: CallbackQuery,
        state: FSMContext,
        bot: Bot,
        subject: str,
    ) -> list[int]:
        await state.update_data(
            subject=subject,
            current_filters=[],
            current_ad_index=0,
            main_message_id=event.message.message_id,
        )
        await state.set_state(TutorSearch.set_filters)
        return await cls.refresh(event, state, bot, event.from_user.id)

    @classmethod
    async def refresh(
        cls,
        event: Message | CallbackQuery,
        state: FSMContext,
        bot: Bot,
        user_id: int,
        reset_index: bool = True,
    ) -> list[int]:
        chat_id = (
            event.message.chat.id if isinstance(event, CallbackQuery) else event.chat.id
        )
        data = await state.get_data()
        subject = data.get("subject", "")
        current_filters = list(data.get("current_filters", []))
        filter_values = {
            name: data.get(name)
            for name in current_filters
            if data.get(name) is not None
        }

        ads = await ad_repo.get_matched_ads(
            subject=subject,
            current_filters=filter_values,
        )
        ad_ids = [ad.ad_id for ad in ads]
        current_index = 0 if reset_index else data.get("current_ad_index", 0)
        if ad_ids:
            current_index = min(current_index, len(ad_ids) - 1)
        else:
            current_index = 0
        await state.update_data(
            cached_ad_ids=ad_ids,
            current_ad_index=current_index,
        )

        main_message_id = data.get("main_message_id")
        if main_message_id:
            try:
                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=main_message_id,
                    text=TutorSearchingViews.header_text(subject, filter_values),
                    reply_markup=TutorSearchingKeyboards.set_filters_keyboard(
                        current_filters
                    ),
                )
            except TelegramBadRequest:
                pass

        await MessageCleaner.purge(bot, chat_id, state)
        return await cls.update_ad_feed(event, state, bot, user_id)

    @classmethod
    async def open_filter(cls, state: FSMContext, filter_name: str) -> bool:
        filter_state = cls.FILTER_STATES.get(filter_name)
        if filter_state is None:
            return False
        await state.set_state(filter_state)
        return True

    @classmethod
    async def set_filter(
        cls,
        state: FSMContext,
        filter_name: str,
        value,
    ) -> None:
        data = await state.get_data()
        filters = list(dict.fromkeys([*data.get("current_filters", []), filter_name]))
        await state.update_data(**{filter_name: value}, current_filters=filters)
        await state.set_state(TutorSearch.set_filters)

    @staticmethod
    async def remove_filter(state: FSMContext, filter_name: str) -> None:
        data = await state.get_data()
        filters = [
            name for name in data.get("current_filters", []) if name != filter_name
        ]
        await state.update_data(**{filter_name: None}, current_filters=filters)
        await state.set_state(TutorSearch.set_filters)

    @staticmethod
    async def shift_page(
        state: FSMContext,
        direction: str,
        expected_index: int,
    ) -> bool:
        data = await state.get_data()
        current_index = data.get("current_ad_index", 0)
        ad_ids = data.get("cached_ad_ids", [])
        if expected_index != current_index or direction not in {"next", "prev"}:
            return False

        last_index = max(0, len(ad_ids) - 1)
        if direction == "next":
            new_index = min(current_index + 1, last_index)
        else:
            new_index = max(0, current_index - 1)
        if new_index == current_index:
            return False
        await state.update_data(current_ad_index=new_index)
        return True

    @staticmethod
    async def set_like(ad_id: int, user_id: int, is_liked: bool) -> None:
        if is_liked:
            await ad_repo.like_ad(ad_id, user_id)
        else:
            await ad_repo.unlike_ad(ad_id, user_id)

    @staticmethod
    async def get_contact_username(ad_id: int) -> str | None:
        ad = await ad_repo.get_by_id(ad_id)
        return ad.tutor_username if ad else None

    @staticmethod
    async def update_ad_feed(
        event: Message | CallbackQuery, state: FSMContext, bot: Bot, user_id: int
    ) -> list[int]:
        """Render the current ad card and clean up the previous card messages."""
        chat_id = (
            event.message.chat.id if isinstance(event, CallbackQuery) else event.chat.id
        )
        data = await state.get_data()

        ad_ids: list[int] = data.get("cached_ad_ids", [])
        current_index: int = data.get("current_ad_index", 0)

        # 1. Clean up previously rendered scrolling card messages
        old_scroll_ids: list[int] = data.get("ads_scrolling_message_id", [])
        if old_scroll_ids:
            try:
                await bot.delete_messages(chat_id=chat_id, message_ids=old_scroll_ids)
            except TelegramBadRequest:
                pass
            await state.update_data(ads_scrolling_message_id=[])

        # 2. Handle empty search results case
        if not ad_ids or current_index >= len(ad_ids):
            empty_msg = await bot.send_message(
                chat_id=chat_id,
                text=TutorSearchingTexts.EMPTY_SEARCH_RESULTS,
                parse_mode=ParseMode.HTML,
            )
            await state.update_data(ads_scrolling_message_id=[empty_msg.message_id])
            return [empty_msg.message_id]

        # 3. Fetch active ad and like status
        ad = None
        while ad_ids:
            target_ad_id = ad_ids[current_index]
            ad = await ad_repo.get_by_id(target_ad_id)
            if ad is not None:
                break
            ad_ids.pop(current_index)
            current_index = min(current_index, max(0, len(ad_ids) - 1))

        if ad is None:
            empty_msg = await bot.send_message(
                chat_id=chat_id,
                text=TutorSearchingTexts.EMPTY_SEARCH_RESULTS,
                parse_mode=ParseMode.HTML,
            )
            await state.update_data(
                cached_ad_ids=[],
                current_ad_index=0,
                ads_scrolling_message_id=[empty_msg.message_id],
            )
            return [empty_msg.message_id]

        await state.update_data(
            cached_ad_ids=ad_ids,
            current_ad_index=current_index,
        )

        is_liked = await ad_repo.is_liked(target_ad_id, user_id)

        # 4. Generate keyboard and formatted text via View layer
        keyboard = TutorSearchingKeyboards.ads_actions_keyboard(
            current_index=current_index,
            total_count=len(ad_ids),
            ad_id=target_ad_id,
            is_liked=is_liked,
        )
        card_text = TutorSearchingViews.ad_position(
            current_index, len(ad_ids)
        ) + render_message(ad)

        new_message_ids = []

        # 5. Render media gallery (if photos exist) + text card
        photos = ad.tutor_photo or []
        if photos:
            media_group = [InputMediaPhoto(media=photo) for photo in photos]
            sent_photos = await bot.send_media_group(chat_id=chat_id, media=media_group)
            new_message_ids.extend([m.message_id for m in sent_photos])

        main_card = await bot.send_message(
            chat_id=chat_id,
            text=card_text,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML,
        )
        new_message_ids.append(main_card.message_id)
        await ad_repo.view_ad(target_ad_id, user_id)

        # 6. Store newly sent card IDs for future cleanup on page shift
        await state.update_data(ads_scrolling_message_id=new_message_ids)
        return new_message_ids
