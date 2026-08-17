import asyncio
import json

from common.utils.action_logging import UserActionLoggingService
from configuration.config import DEFAULT_ADMIN_ID


class FakeBot:
    def __init__(self):
        self.sent = []

    async def send_message(self, chat_id, text):
        self.sent.append((chat_id, text))


def _action(user_id: int, **overrides):
    action = {
        "user_id": user_id,
        "chat_id": user_id,
        "event_type": "Message",
        "handler_name": "sample_handler",
        "processing_time_ms": 10,
        "status_code": "success",
        "state": "BotFlow:menu_navigation",
    }
    action.update(overrides)
    return action


def test_action_logger_writes_file_and_warns_only_admin_view(tmp_path):
    async def scenario():
        bot = FakeBot()
        service = UserActionLoggingService(
            log_path=tmp_path / "user_actions.jsonl",
            slow_threshold_seconds=1,
        )

        await service.record(_action(123), bot=bot)
        await service.record(
            _action(123, processing_time_ms=1500, handler_name="slow_handler"),
            bot=bot,
        )
        assert bot.sent == []

        await service.record(
            _action(
                DEFAULT_ADMIN_ID,
                chat_id=999,
                state="AdminFlow:menu_navigation",
                handler_name="enter_admin_view",
            ),
            bot=bot,
        )
        await service.record(
            _action(123, processing_time_ms=1500, handler_name="slow_handler"),
            bot=bot,
        )
        return bot, service.log_path

    bot, log_path = asyncio.run(scenario())

    assert len(bot.sent) == 1
    assert bot.sent[0][0] == 999
    assert "slow_handler" in bot.sent[0][1]
    assert "5 действий пользователя до этого" in bot.sent[0][1]

    lines = log_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 4
    assert json.loads(lines[-1])["handler_name"] == "slow_handler"
