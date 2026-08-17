import asyncio
import logging

from aiogram import Bot
from aiogram.exceptions import (
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramRetryAfter,
)
from aiogram.types import InlineKeyboardMarkup
from infrastructure.database import notify_repo

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self, bot: Bot):
        self.bot = bot

    @staticmethod
    async def delete_owned(notification_id: int, user_id: int) -> bool:
        return await notify_repo.delete_notification(notification_id, user_id)

    async def send_notification(
        self, user_id: int, text: str, reply_markup: InlineKeyboardMarkup | None = None
    ) -> bool:
        """Sends a single notification with error handling for Telegram limits."""
        try:
            await self.bot.send_message(
                chat_id=user_id, text=text, reply_markup=reply_markup, parse_mode="HTML"
            )
            return True

        except TelegramForbiddenError:
            # User blocked the bot
            logger.warning(f"Failed to notify user {user_id}: Bot blocked by user.")
            # Optional: Mark user as inactive in your DB here
            return False

        except TelegramRetryAfter as e:
            # Hit Telegram rate limit: pause for required duration and retry
            logger.warning(
                f"Rate limited by Telegram. Waiting {e.retry_after} seconds."
            )
            await asyncio.sleep(e.retry_after)
            return await self.send_notification(user_id, text, reply_markup)

        except TelegramBadRequest as e:
            logger.error(f"Failed to notify user {user_id}: {e}")
            return False

    async def broadcast_free_ad_promo(
        self,
        user_ids: list[int],
        text: str,
        reply_markup: InlineKeyboardMarkup | None = None,
    ) -> dict[str, int]:
        """Broadcasts notification to a batch of users safely."""
        success_count = 0
        fail_count = 0

        for user_id in user_ids:
            sent = await self.send_notification(user_id, text, reply_markup)
            if sent:
                success_count += 1
            else:
                fail_count += 1

            # Safe delay to stay well under 30 msg/sec global limit
            await asyncio.sleep(0.05)  # max ~20 messages/sec

        return {"success": success_count, "failed": fail_count}
