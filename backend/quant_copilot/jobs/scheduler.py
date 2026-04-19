from __future__ import annotations

from dataclasses import dataclass
from typing import Awaitable, Callable

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger


AsyncJob = Callable[[], Awaitable[None]]


@dataclass
class Scheduler:
    scheduler: AsyncIOScheduler

    def start(self) -> None:
        if not self.scheduler.running:
            self.scheduler.start()

    def shutdown(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)


def build_scheduler(
    *,
    archive: AsyncJob,
    backup: AsyncJob,
    outcomes: AsyncJob,
    watchlist_poll: AsyncJob,
    tz: str = "Asia/Kolkata",
) -> Scheduler:
    sch = AsyncIOScheduler(timezone=tz)

    # Nightly archival at 23:00 IST
    sch.add_job(archive, CronTrigger(hour=23, minute=0), id="archive", replace_existing=True)
    # Nightly backup at 23:30 IST
    sch.add_job(backup,  CronTrigger(hour=23, minute=30), id="backup", replace_existing=True)
    # Outcomes job 01:00 IST (after the target date has rolled)
    sch.add_job(outcomes, CronTrigger(hour=1, minute=0), id="outcomes", replace_existing=True)
    # Watchlist poll every 15 minutes during market hours (09:15–15:30 IST, Mon–Fri)
    sch.add_job(
        watchlist_poll,
        CronTrigger(day_of_week="mon-fri", hour="9-15", minute="*/15"),
        id="watchlist_poll",
        replace_existing=True,
    )
    return Scheduler(scheduler=sch)
