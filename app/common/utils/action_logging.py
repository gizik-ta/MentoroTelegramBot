import json
import logging
import os
from collections import defaultdict, deque
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from threading import RLock
from typing import Any

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from configuration.config import config

logger = logging.getLogger(__name__)


def _slow_threshold() -> float:
    raw_value = os.getenv("SLOW_HANDLER_WARNING_SECONDS", "1")
    try:
        return max(0.1, float(raw_value))
    except ValueError:
        return 1.0


class UserActionLoggingService:
    """Append user action middleware records and alert admins in admin view."""

    def __init__(
        self,
        log_path: Path | None = None,
        slow_threshold_seconds: float | None = None,
    ) -> None:
        self.log_path = log_path or Path(__file__).with_name("user_actions.jsonl")
        self.slow_threshold_seconds = (
            slow_threshold_seconds
            if slow_threshold_seconds is not None
            else _slow_threshold()
        )
        self._lock = RLock()
        self._recent_by_user: defaultdict[int, deque[dict[str, Any]]] = defaultdict(
            lambda: deque(maxlen=50)
        )
        self._admin_view_chat_ids: dict[int, int] = {}

    async def record(self, action: dict[str, Any], bot: Bot | None = None) -> None:
        entry = self._normalize(action)
        user_id = entry.get("user_id")

        with self._lock:
            previous_actions = self._previous_actions(user_id, limit=5)
            self._append(entry)
            if isinstance(user_id, int):
                self._recent_by_user[user_id].append(entry)
            self._sync_admin_view(entry)

        if self._should_warn(entry):
            await self._warn_admins(bot, entry, previous_actions)

    def warning_history(self) -> list[dict[str, Any]]:
        """Rebuild every persisted slow/error warning with its prior context."""

        if not self.log_path.exists():
            return []

        recent_by_user: defaultdict[int, deque[dict[str, Any]]] = defaultdict(
            lambda: deque(maxlen=5)
        )
        warnings: list[dict[str, Any]] = []
        try:
            with self._lock, self.log_path.open("r", encoding="utf-8") as log_file:
                for line in log_file:
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    user_id = entry.get("user_id")
                    previous = (
                        list(recent_by_user[user_id])
                        if isinstance(user_id, int)
                        else []
                    )
                    if self._should_warn(entry):
                        warnings.append(
                            {
                                "timestamp_utc": entry.get("timestamp_utc"),
                                "text": self._warning_text(entry, previous),
                            }
                        )
                    if isinstance(user_id, int):
                        recent_by_user[user_id].append(entry)
        except OSError:
            return []
        return warnings

    def _normalize(self, action: dict[str, Any]) -> dict[str, Any]:
        entry = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "user_id": action.get("user_id"),
            "chat_id": action.get("chat_id"),
            "event_type": action.get("event_type"),
            "handler_name": action.get("handler_name"),
            "processing_time_ms": action.get("processing_time_ms"),
            "status_code": action.get("status_code"),
            "state": action.get("state"),
        }
        if action.get("error_text"):
            entry["error_text"] = str(action["error_text"])[:500]
        return entry

    def _previous_actions(
        self,
        user_id: int | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        if not isinstance(user_id, int):
            return []

        cached = list(self._recent_by_user[user_id])
        if cached:
            return cached[-limit:]

        if not self.log_path.exists():
            return []

        found: list[dict[str, Any]] = []
        try:
            with self.log_path.open("r", encoding="utf-8") as log_file:
                for line in log_file:
                    try:
                        item = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if item.get("user_id") == user_id:
                        found.append(item)
        except OSError as error:
            logger.warning("Could not read user action log: %s", error)
            return []

        return found[-limit:]

    def _append(self, entry: dict[str, Any]) -> None:
        try:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            with self.log_path.open("a", encoding="utf-8") as log_file:
                log_file.write(json.dumps(entry, ensure_ascii=False) + "\n")
                log_file.flush()
        except OSError as error:
            logger.warning("Could not write user action log: %s", error)

    def _sync_admin_view(self, entry: dict[str, Any]) -> None:
        user_id = entry.get("user_id")
        chat_id = entry.get("chat_id")
        state = str(entry.get("state") or "")

        if not isinstance(user_id, int) or user_id not in config.admin_ids:
            return
        if state.startswith("AdminFlow:") and isinstance(chat_id, int):
            self._admin_view_chat_ids[user_id] = chat_id
        else:
            self._admin_view_chat_ids.pop(user_id, None)

    def _should_warn(self, entry: dict[str, Any]) -> bool:
        processing_time_ms = entry.get("processing_time_ms")
        is_slow = (
            isinstance(processing_time_ms, (int, float))
            and processing_time_ms > self.slow_threshold_seconds * 1000
        )
        return entry.get("status_code") == "error" or is_slow

    async def _warn_admins(
        self,
        bot: Bot | None,
        entry: dict[str, Any],
        previous_actions: list[dict[str, Any]],
    ) -> None:
        if bot is None or not self._admin_view_chat_ids:
            return

        text = self._warning_text(entry, previous_actions)
        for chat_id in set(self._admin_view_chat_ids.values()):
            try:
                await bot.send_message(chat_id=chat_id, text=text)
            except TelegramAPIError as error:
                logger.warning("Could not send user action warning: %s", error)

    def _warning_text(
        self,
        entry: dict[str, Any],
        previous_actions: list[dict[str, Any]],
    ) -> str:
        lines = [
            "<b>Предупреждение по обработчику</b>",
            f"User ID: {escape(str(entry.get('user_id')))}",
            f"Handler: {escape(str(entry.get('handler_name')))}",
            f"Time: {escape(str(entry.get('processing_time_ms')))} ms",
            f"Status: {escape(str(entry.get('status_code')))}",
        ]

        if entry.get("error_text"):
            lines.append(f"Error: {escape(str(entry['error_text']))}")

        lines.append("")
        lines.append("5 действий пользователя до этого:")
        if previous_actions:
            for item in previous_actions[-5:]:
                lines.append(self._history_line(item))
        else:
            lines.append("Нет предыдущих действий.")

        return "\n".join(lines)[:3500]

    @staticmethod
    def _history_line(item: dict[str, Any]) -> str:
        timestamp = str(item.get("timestamp_utc") or "")
        handler = str(item.get("handler_name") or "")
        status = str(item.get("status_code") or "")
        elapsed = str(item.get("processing_time_ms") or "")
        return (
            f"- {escape(timestamp)} | {escape(handler)} | "
            f"{escape(status)} | {escape(elapsed)} ms"
        )


user_action_logger = UserActionLoggingService()
