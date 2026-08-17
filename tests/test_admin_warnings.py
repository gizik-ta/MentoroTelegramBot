import asyncio

from common.utils.action_logging import UserActionLoggingService


def test_warning_history_contains_all_persisted_slow_and_error_actions(tmp_path):
    async def scenario():
        service = UserActionLoggingService(
            log_path=tmp_path / "actions.jsonl",
            slow_threshold_seconds=1,
        )
        base = {
            "user_id": 123,
            "chat_id": 123,
            "event_type": "Message",
            "state": "BotFlow:menu_navigation",
        }
        await service.record(
            {
                **base,
                "handler_name": "normal_handler",
                "processing_time_ms": 10,
                "status_code": "success",
            }
        )
        await service.record(
            {
                **base,
                "handler_name": "slow_handler",
                "processing_time_ms": 1500,
                "status_code": "success",
            }
        )
        await service.record(
            {
                **base,
                "handler_name": "broken_handler",
                "processing_time_ms": 20,
                "status_code": "error",
                "error_text": "ValueError: broken",
            }
        )
        return service.warning_history()

    warnings = asyncio.run(scenario())

    assert len(warnings) == 2
    assert "slow_handler" in warnings[0]["text"]
    assert "normal_handler" in warnings[0]["text"]
    assert "broken_handler" in warnings[1]["text"]
    assert "ValueError: broken" in warnings[1]["text"]
