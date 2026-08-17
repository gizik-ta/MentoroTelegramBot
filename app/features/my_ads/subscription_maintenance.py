import asyncio
from datetime import date, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import aiosqlite
from infrastructure.database import subscription_repo

from .texts import MyAdsTexts


class SubscriptionMaintenanceService:
    """Run idempotent publication expiration and reminder work once per day."""

    def __init__(self, timezone_name: str, repository=None) -> None:
        try:
            self.timezone = ZoneInfo(timezone_name)
        except ZoneInfoNotFoundError:
            self.timezone = ZoneInfo("UTC")
        self.repository = repository or subscription_repo
        self._last_processed_date: date | None = None
        self._stop_event = asyncio.Event()
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        self._stop_event.clear()
        await self.run_once()
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(
                self._run(),
                name="pomogator-subscription-maintenance",
            )

    async def stop(self) -> None:
        self._stop_event.set()
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None

    async def run_once(self, current_date: date | None = None) -> dict[str, int]:
        effective_date = current_date or datetime.now(self.timezone).date()
        result = await self.repository.process_day(
            effective_date,
            MyAdsTexts.PUBLICATION_END_REMINDER,
        )
        self._last_processed_date = effective_date
        return result

    async def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=60)
                continue
            except TimeoutError:
                pass

            today = datetime.now(self.timezone).date()
            if today == self._last_processed_date:
                continue
            try:
                await self.run_once(today)
            except (aiosqlite.Error, RuntimeError):
                # Keep the date unprocessed so the next short cycle retries it.
                await asyncio.sleep(0)
