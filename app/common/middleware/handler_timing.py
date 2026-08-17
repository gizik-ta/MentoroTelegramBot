from collections.abc import Awaitable, Callable
from time import perf_counter
from typing import Any

from aiogram import BaseMiddleware, Dispatcher
from aiogram.exceptions import TelegramAPIError
from aiogram.types import TelegramObject
from common.utils.action_logging import UserActionLoggingService, user_action_logger


class HandlerTimingMiddleware(BaseMiddleware):
    """Log the outcome and execution time of every Telegram handler."""

    def __init__(
        self,
        action_logger: UserActionLoggingService | None = None,
    ) -> None:
        self.action_logger = action_logger or user_action_logger

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        started_at = perf_counter()
        status_code = "success"
        error_text: str | None = None

        try:
            return await handler(event, data)
        except Exception as error:
            status_code = "error"
            error_text = self._safe_error_text(error)
            raise
        finally:
            elapsed_ms = round((perf_counter() - started_at) * 1000, 3)
            payload = {
                "user_id": self._user_id(event, data),
                "chat_id": self._chat_id(event, data),
                "event_type": event.__class__.__name__,
                "handler_name": self._handler_name(handler, data),
                "processing_time_ms": elapsed_ms,
                "status_code": status_code,
                "state": await self._state_name(data),
            }
            if error_text is not None:
                payload["error_text"] = error_text
            await self._record_action(payload, event, data)

    @staticmethod
    def _user_id(event: TelegramObject, data: dict[str, Any]) -> int | None:
        user = data.get("event_from_user") or getattr(event, "from_user", None)
        return getattr(user, "id", None)

    @staticmethod
    def _chat_id(event: TelegramObject, data: dict[str, Any]) -> int | None:
        chat = data.get("event_chat") or getattr(event, "chat", None)
        if chat is None:
            message = getattr(event, "message", None)
            chat = getattr(message, "chat", None)
        return getattr(chat, "id", None)

    @staticmethod
    def _handler_name(
        handler: Callable[..., Awaitable[Any]],
        data: dict[str, Any],
    ) -> str:
        handler_object = data.get("handler")
        callback = getattr(handler_object, "callback", None)
        resolved_handler = callback or handler
        return getattr(
            resolved_handler,
            "__qualname__",
            resolved_handler.__class__.__name__,
        )

    @staticmethod
    def _safe_error_text(error: Exception) -> str:
        details = str(error).replace("\r", " ").replace("\n", " ").strip()
        if len(details) > 500:
            details = f"{details[:497]}..."
        return f"{type(error).__name__}: {details}"

    @staticmethod
    async def _state_name(data: dict[str, Any]) -> str | None:
        state = data.get("state")
        if state is None or not hasattr(state, "get_state"):
            return None
        try:
            return await state.get_state()
        except (AttributeError, RuntimeError, TypeError):
            return None

    async def _record_action(
        self,
        payload: dict[str, Any],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> None:
        try:
            bot = data.get("bot") or getattr(event, "bot", None)
            await self.action_logger.record(payload, bot=bot)
        except (OSError, RuntimeError, TelegramAPIError):
            # Action logging must never break the Telegram update itself.
            pass


def register_handler_timing(dispatcher: Dispatcher) -> None:
    """Register one inner middleware for every supported handler event type."""

    middleware = HandlerTimingMiddleware()
    for event_name, observer in dispatcher.observers.items():
        if event_name not in {"update", "error"}:
            observer.middleware(middleware)
