from aiogram import Router
from aiogram.types import Message

fallback_router = Router()


@fallback_router.message()
async def ignore_unmatched_message(message: Message) -> None:
    """Consume unmatched input; the session middleware keeps it for later cleanup."""
