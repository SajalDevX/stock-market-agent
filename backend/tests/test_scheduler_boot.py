from quant_copilot.jobs.scheduler import Scheduler, build_scheduler
from apscheduler.schedulers.asyncio import AsyncIOScheduler


def test_build_scheduler_registers_jobs():
    async def _job():
        pass

    sch = build_scheduler(
        archive=_job, backup=_job, outcomes=_job, watchlist_poll=_job,
        tz="Asia/Kolkata",
    )
    assert isinstance(sch, Scheduler)
    ids = {j.id for j in sch.scheduler.get_jobs()}
    assert {"archive", "backup", "outcomes", "watchlist_poll"}.issubset(ids)
    # APScheduler created with IST timezone
    assert str(sch.scheduler.timezone) == "Asia/Kolkata"
