"""APScheduler-backed background dreaming."""
from __future__ import annotations

import logging
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler

from .config import Config
from .memory import MemoryStore
from .dreamer import dream_cycle

logger = logging.getLogger(__name__)

_scheduler: Optional[BackgroundScheduler] = None


def start_scheduler(store: MemoryStore, config: Optional[Config] = None) -> BackgroundScheduler:
    """Start the background dream scheduler. Runs dream_cycle every N minutes."""
    global _scheduler
    cfg = config or Config.from_env()

    if _scheduler and _scheduler.running:
        return _scheduler

    _scheduler = BackgroundScheduler()
    _scheduler.add_job(
        lambda: dream_cycle(store=store, config=cfg),
        trigger="interval",
        minutes=cfg.dream_interval_minutes,
        id="dream_cycle",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info(
        "Dream scheduler started (interval: %d min)", cfg.dream_interval_minutes
    )
    return _scheduler


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Dream scheduler stopped")
