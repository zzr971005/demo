"""
APScheduler ä»»å¡è°åº¦å?â?Task 11

èè´£ï¼?- æ¯æ 20:30 è§¦åè¿å
- æ¯ç§é£æ§çæ§
- æ¯åéä»ä½å¯¹è´?- æ¯æ¥æ¶çå?Regime è®¡ç®
- ä¸?candidate_coreãrisk_monitor èå¨
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Coroutine, Dict, List, Optional

from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.config import get_settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# ä»»å¡å®ä¹
# ---------------------------------------------------------------------------

@dataclass
class ScheduledJob:
    """è°åº¦ä»»å¡åæ°æ?""

    id: str
    name: str
    func: Callable[..., Coroutine[Any, Any, Any]]
    trigger: Any
    max_instances: int = 1
    misfire_grace_time: int = 300
    next_run_time: Optional[datetime] = None
    last_run_time: Optional[datetime] = None
    last_result: Optional[Any] = None
    last_error: Optional[str] = None
    run_count: int = 0
    fail_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "max_instances": self.max_instances,
            "misfire_grace_time": self.misfire_grace_time,
            "next_run_time": self.next_run_time.isoformat() if self.next_run_time else None,
            "last_run_time": self.last_run_time.isoformat() if self.last_run_time else None,
            "last_error": self.last_error,
            "run_count": self.run_count,
            "fail_count": self.fail_count,
        }


# ---------------------------------------------------------------------------
# è°åº¦å¨å°è£?# ---------------------------------------------------------------------------

class QuantScheduler:
    """
    éåç³»ç»ä»»å¡è°åº¦å?
    åºäº APScheduler çå¼æ­¥è°åº¦å°è£ï¼æä¾ï¼?    - è¿åä»»å¡ï¼æ¯æ?20:30ï¼?    - é£æ§çæ§ï¼æ¯ç§ï¼
    - ä»ä½å¯¹è´¦ï¼æ¯åéï¼?    - Regime è®¡ç®ï¼æ¯æ¥æ¶çåï¼?    """

    def __init__(self, redis_client: Optional[Any] = None) -> None:
        self.scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")
        self.redis = redis_client
        self._jobs: Dict[str, ScheduledJob] = {}
        self._running = False
        self._lock = asyncio.Lock()

        # æ³¨åäºä»¶çå¬
        self.scheduler.add_listener(
            self._on_job_event,
            EVENT_JOB_EXECUTED | EVENT_JOB_ERROR,
        )

    # -----------------------------------------------------------------------
    # çå½å¨æ
    # -----------------------------------------------------------------------

    def start(self) -> None:
        """å¯å¨è°åº¦å¨ã?""
        if self._running:
            return
        self.scheduler.start()
        self._running = True
        logger.info("APScheduler å·²å¯å?)

    def shutdown(self, wait: bool = True) -> None:
        """å³é­è°åº¦å¨ã?""
        if not self._running:
            return
        self.scheduler.shutdown(wait=wait)
        self._running = False
        logger.info("APScheduler å·²å³é?)

    @property
    def is_running(self) -> bool:
        return self._running

    # -----------------------------------------------------------------------
    # ä»»å¡æ³¨å
    # -----------------------------------------------------------------------

    def add_evolution_job(
        self,
        func: Callable[..., Coroutine[Any, Any, Any]],
        hour: int = 20,
        minute: int = 30,
        **kwargs: Any,
    ) -> str:
        """
        æ³¨åè¿åä»»å¡ã?
        é»è®¤æ¯æ 20:30 æ§è¡ã?        """
        job_id = "evolution_daily"
        trigger = CronTrigger(hour=hour, minute=minute, timezone="Asia/Shanghai")

        self.scheduler.add_job(
            func=func,
            trigger=trigger,
            id=job_id,
            name="æ¯æ¥è¿å",
            max_instances=1,
            misfire_grace_time=600,
            replace_existing=True,
            **kwargs,
        )

        self._jobs[job_id] = ScheduledJob(
            id=job_id,
            name="æ¯æ¥è¿å",
            func=func,
            trigger=trigger,
        )
        logger.info(f"è¿åä»»å¡å·²æ³¨å? æ¯å¤© {hour:02d}:{minute:02d}")
        return job_id

    def add_risk_monitor_job(
        self,
        func: Callable[..., Coroutine[Any, Any, Any]],
        interval_seconds: float = 1.0,
        **kwargs: Any,
    ) -> str:
        """
        æ³¨åé£æ§çæ§ä»»å¡ã?
        é»è®¤æ¯ç§æ§è¡ä¸æ¬¡ã?        """
        job_id = "risk_monitor"
        trigger = IntervalTrigger(seconds=interval_seconds)

        self.scheduler.add_job(
            func=func,
            trigger=trigger,
            id=job_id,
            name="é£æ§çæ§",
            max_instances=1,
            misfire_grace_time=5,
            replace_existing=True,
            **kwargs,
        )

        self._jobs[job_id] = ScheduledJob(
            id=job_id,
            name="é£æ§çæ§",
            func=func,
            trigger=trigger,
        )
        logger.info(f"é£æ§çæ§ä»»å¡å·²æ³¨å? æ¯?{interval_seconds}s")
        return job_id

    def add_reconciliation_job(
        self,
        func: Callable[..., Coroutine[Any, Any, Any]],
        interval_minutes: int = 1,
        **kwargs: Any,
    ) -> str:
        """
        æ³¨åä»ä½å¯¹è´¦ä»»å¡ã?
        é»è®¤æ¯åéæ§è¡ä¸æ¬¡ã?        """
        job_id = "reconciliation"
        trigger = IntervalTrigger(minutes=interval_minutes)

        self.scheduler.add_job(
            func=func,
            trigger=trigger,
            id=job_id,
            name="ä»ä½å¯¹è´¦",
            max_instances=1,
            misfire_grace_time=30,
            replace_existing=True,
            **kwargs,
        )

        self._jobs[job_id] = ScheduledJob(
            id=job_id,
            name="ä»ä½å¯¹è´¦",
            func=func,
            trigger=trigger,
        )
        logger.info(f"ä»ä½å¯¹è´¦ä»»å¡å·²æ³¨å? æ¯?{interval_minutes}min")
        return job_id

    def add_regime_job(
        self,
        func: Callable[..., Coroutine[Any, Any, Any]],
        hour: int = 15,
        minute: int = 30,
        **kwargs: Any,
    ) -> str:
        """
        æ³¨å Regime è®¡ç®ä»»å¡ã?
        é»è®¤æ¯æ¥æ¶çå?15:30 æ§è¡ï¼åè®¾æè´§æ¶çæ¶é´ï¼ã?        """
        job_id = "regime_calc"
        trigger = CronTrigger(hour=hour, minute=minute, timezone="Asia/Shanghai")

        self.scheduler.add_job(
            func=func,
            trigger=trigger,
            id=job_id,
            name="Regimeè®¡ç®",
            max_instances=1,
            misfire_grace_time=1800,
            replace_existing=True,
            **kwargs,
        )

        self._jobs[job_id] = ScheduledJob(
            id=job_id,
            name="Regimeè®¡ç®",
            func=func,
            trigger=trigger,
        )
        logger.info(f"Regimeä»»å¡å·²æ³¨å? æ¯å¤© {hour:02d}:{minute:02d}")
        return job_id

    def add_custom_job(
        self,
        job_id: str,
        name: str,
        func: Callable[..., Coroutine[Any, Any, Any]],
        trigger: Any,
        max_instances: int = 1,
        misfire_grace_time: int = 300,
        **kwargs: Any,
    ) -> str:
        """æ³¨åèªå®ä¹ä»»å¡ã?""
        self.scheduler.add_job(
            func=func,
            trigger=trigger,
            id=job_id,
            name=name,
            max_instances=max_instances,
            misfire_grace_time=misfire_grace_time,
            replace_existing=True,
            **kwargs,
        )

        self._jobs[job_id] = ScheduledJob(
            id=job_id,
            name=name,
            func=func,
            trigger=trigger,
            max_instances=max_instances,
            misfire_grace_time=misfire_grace_time,
        )
        logger.info(f"èªå®ä¹ä»»å¡å·²æ³¨å: {name} ({job_id})")
        return job_id

    def remove_job(self, job_id: str) -> bool:
        """ç§»é¤ä»»å¡ã?""
        try:
            self.scheduler.remove_job(job_id)
            self._jobs.pop(job_id, None)
            logger.info(f"ä»»å¡å·²ç§»é? {job_id}")
            return True
        except Exception as e:
            logger.warning(f"ç§»é¤ä»»å¡å¤±è´¥ {job_id}: {e}")
            return False

    def pause_job(self, job_id: str) -> bool:
        """æåä»»å¡ã?""
        try:
            self.scheduler.pause_job(job_id)
            logger.info(f"ä»»å¡å·²æå? {job_id}")
            return True
        except Exception as e:
            logger.warning(f"æåä»»å¡å¤±è´¥ {job_id}: {e}")
            return False

    def resume_job(self, job_id: str) -> bool:
        """æ¢å¤ä»»å¡ã?""
        try:
            self.scheduler.resume_job(job_id)
            logger.info(f"ä»»å¡å·²æ¢å¤? {job_id}")
            return True
        except Exception as e:
            logger.warning(f"æ¢å¤ä»»å¡å¤±è´¥ {job_id}: {e}")
            return False

    # -----------------------------------------------------------------------
    # äºä»¶å¤ç
    # -----------------------------------------------------------------------

    def _on_job_event(self, event: Any) -> None:
        """çå¬ä»»å¡æ§è¡äºä»¶ã?""
        job_id = event.job_id
        job_meta = self._jobs.get(job_id)
        if job_meta is None:
            return

        job_meta.last_run_time = datetime.utcnow()
        job_meta.run_count += 1

        if event.exception:
            job_meta.last_error = str(event.exception)
            job_meta.fail_count += 1
            logger.error(f"[{job_id}] ä»»å¡æ§è¡å¤±è´¥: {event.exception}")
        else:
            job_meta.last_error = None
            job_meta.last_result = getattr(event, "retval", None)
            logger.debug(f"[{job_id}] ä»»å¡æ§è¡æå")

    # -----------------------------------------------------------------------
    # æ¥è¯¢æ¥å£
    # -----------------------------------------------------------------------

    def get_job(self, job_id: str) -> Optional[ScheduledJob]:
        """è·åä»»å¡åæ°æ®ã?""
        return self._jobs.get(job_id)

    def list_jobs(self) -> List[ScheduledJob]:
        """ååºææå·²æ³¨åä»»å¡ã?""
        return list(self._jobs.values())

    def get_scheduler_jobs(self) -> List[Any]:
        """è·å APScheduler åçä»»å¡åè¡¨ã?""
        return self.scheduler.get_jobs()

    def get_next_run_times(self) -> Dict[str, Optional[datetime]]:
        """è·åææä»»å¡çä¸æ¬¡æ§è¡æ¶é´ã?""
        result = {}
        for job in self.scheduler.get_jobs():
            result[job.id] = job.next_run_time
        return result


# ---------------------------------------------------------------------------
# ä¾¿æ·æé å¨
# ---------------------------------------------------------------------------

class SchedulerBuilder:
    """
    è°åº¦å¨ä¾¿æ·æé å¨

    ä¸é®éç½®ç³»ç»æéçæææ åä»»å¡ã?    """

    def __init__(self, scheduler: QuantScheduler) -> None:
        self.scheduler = scheduler

    def build_standard_schedule(
        self,
        evolution_func: Optional[Callable[..., Coroutine[Any, Any, Any]]] = None,
        risk_func: Optional[Callable[..., Coroutine[Any, Any, Any]]] = None,
        reconciliation_func: Optional[Callable[..., Coroutine[Any, Any, Any]]] = None,
        regime_func: Optional[Callable[..., Coroutine[Any, Any, Any]]] = None,
    ) -> List[str]:
        """
        æå»ºæ åè°åº¦éç½®ã?
        æ³¨ååä¸ªæ ¸å¿ä»»å¡ï¼?        - evolution_daily
        - risk_monitor
        - reconciliation
        - regime_calc
        """
        job_ids = []

        if evolution_func:
            settings = get_settings()
            evo_time = settings.system.evolution.daily_evolution_time if settings.system else "20:30"
            hour, minute = map(int, evo_time.split(":"))
            jid = self.scheduler.add_evolution_job(evolution_func, hour=hour, minute=minute)
            job_ids.append(jid)

        if risk_func:
            jid = self.scheduler.add_risk_monitor_job(risk_func, interval_seconds=1.0)
            job_ids.append(jid)

        if reconciliation_func:
            jid = self.scheduler.add_reconciliation_job(reconciliation_func, interval_minutes=1)
            job_ids.append(jid)

        if regime_func:
            jid = self.scheduler.add_regime_job(regime_func, hour=15, minute=30)
            job_ids.append(jid)

        logger.info(f"æ åè°åº¦éç½®å®æï¼å± {len(job_ids)} ä¸ªä»»å?)
        return job_ids
