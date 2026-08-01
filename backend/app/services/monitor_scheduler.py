"""In-process six-hour scheduler for backend monitoring acquisition."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from app.repositories.monitor_snapshot_store import MONITOR_BUCKET_HOURS, monitor_bucket_start
from app.services.monitor_acquisition import MonitorAcquisitionService

logger = logging.getLogger(__name__)


def seconds_until_next_bucket(now: datetime | None = None) -> float:
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    next_bucket = monitor_bucket_start(current) + timedelta(hours=MONITOR_BUCKET_HOURS)
    return max(1.0, (next_bucket - current).total_seconds())


class MonitorScheduler:
    def __init__(self, service: MonitorAcquisitionService) -> None:
        self.service = service
        self._task: asyncio.Task[None] | None = None

    def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._run(), name="mazu-monitor-refresh")

    async def stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None

    async def _run(self) -> None:
        while True:
            outcomes = await asyncio.to_thread(self.service.refresh_configured_sources)
            logger.info("monitor refresh completed: %s", outcomes)
            await asyncio.sleep(seconds_until_next_bucket())
