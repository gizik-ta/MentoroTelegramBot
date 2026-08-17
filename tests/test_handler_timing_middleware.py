import asyncio
from types import SimpleNamespace

import pytest
from common.middleware.handler_timing import HandlerTimingMiddleware


class FakeActionLogger:
    def __init__(self):
        self.records = []

    async def record(self, payload, bot=None):
        self.records.append((payload, bot))


def test_handler_timing_records_success_without_standard_logging():
    async def scenario():
        async def sample_handler(event, data):
            return "done"

        action_logger = FakeActionLogger()
        middleware = HandlerTimingMiddleware(action_logger=action_logger)
        data = {
            "event_from_user": SimpleNamespace(id=42),
            "handler": SimpleNamespace(callback=sample_handler),
        }
        result = await middleware(sample_handler, object(), data)
        return result, action_logger

    result, action_logger = asyncio.run(scenario())
    assert result == "done"
    payload = action_logger.records[-1][0]
    assert payload["user_id"] == 42
    assert payload["handler_name"].endswith("sample_handler")
    assert payload["processing_time_ms"] >= 0
    assert payload["status_code"] == "success"
    assert "error_text" not in payload


def test_handler_timing_records_error_and_reraises():
    action_logger = FakeActionLogger()

    async def scenario():
        async def broken_handler(event, data):
            raise ValueError("broken")

        middleware = HandlerTimingMiddleware(action_logger=action_logger)
        data = {
            "event_from_user": SimpleNamespace(id=84),
            "handler": SimpleNamespace(callback=broken_handler),
        }
        await middleware(broken_handler, object(), data)

    with pytest.raises(ValueError, match="broken"):
        asyncio.run(scenario())

    payload = action_logger.records[-1][0]
    assert payload["user_id"] == 84
    assert payload["handler_name"].endswith("broken_handler")
    assert payload["status_code"] == "error"
    assert payload["error_text"] == "ValueError: broken"
