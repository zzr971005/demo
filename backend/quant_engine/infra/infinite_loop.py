"""
æ éä¸»å¾ªç?â?Task 11

èè´£ï¼?- æè´§ä¼å¸æ¶æåä¸»å¾ªç¯
- å¼çåé¢ç­
- æ­ç¹ç»­ä¼ ï¼æ¢å¤ä¸æ¬¡è¿è¡ç¶æï¼
- å¼å¸¸æ¢å¤ä¸ææ°éé¿éè¯?"""

from __future__ import annotations

import asyncio
import json
import logging
import pickle
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Coroutine, Dict, List, Optional, Tuple

from app.config import get_settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# ç¶æå®ä¹?# ---------------------------------------------------------------------------

class LoopState(str, Enum):
    IDLE = "IDLE"
    PREHEAT = "PREHEAT"          # å¼çåé¢ç­
    RUNNING = "RUNNING"
    MARKET_CLOSED = "MARKET_CLOSED"  # ä¼å¸æå
    PAUSED = "PAUSED"            # æå¨æå
    RECOVERING = "RECOVERING"    # å¼å¸¸æ¢å¤ä¸?    STOPPED = "STOPPED"


# ---------------------------------------------------------------------------
# äº¤ææ¶æ®µå¤æ­
# ---------------------------------------------------------------------------

class TradingCalendar:
    """äº¤ææ¶æ®µå¤æ­å¨ï¼ç®åçï¼æ¯ææ¥ç?å¤çï¼ã?""

    DAY_SESSION_START = time(8, 55)
    DAY_SESSION_END = time(15, 5)
    NIGHT_SESSION_START = time(20, 55)
    NIGHT_SESSION_END = time(2, 35)

    def __init__(self, symbol_configs: Optional[Dict[str, Any]] = None) -> None:
        self.symbol_configs = symbol_configs or {}

    def is_trading_time(self, dt: Optional[datetime] = None) -> bool:
        """å¤æ­å½åæ¯å¦ä¸ºäº¤ææ¶é´ã?""
        now = dt or datetime.now()
        t = now.time()
        weekday = now.weekday()

        # å¨æ«ä¼å¸
        if weekday >= 5:
            return False

        # æ¥ç
        if self.DAY_SESSION_START <= t <= self.DAY_SESSION_END:
            return True

        # å¤çï¼è·¨å¤©ï¼
        if t >= self.NIGHT_SESSION_START or t <= self.NIGHT_SESSION_END:
            return True

        return False

    def seconds_to_next_open(self, dt: Optional[datetime] = None) -> float:
        """è®¡ç®è·ç¦»ä¸æ¬¡å¼ççç§æ°ã?""
        now = dt or datetime.now()
        t = now.time()
        weekday = now.weekday()

        # å¨æ«ç´æ¥è·³å°å¨ä¸æ©ç
        if weekday >= 5:
            days_to_monday = 7 - weekday
            next_open = datetime.combine(
                now.date() + timedelta(days=days_to_monday),
                self.DAY_SESSION_START,
            )
            return (next_open - now).total_seconds()

        # æ¥çå?        if t < self.DAY_SESSION_START:
            next_open = datetime.combine(now.date(), self.DAY_SESSION_START)
            return (next_open - now).total_seconds()

        # æ¥çç»æåï¼å¤çå?        if self.DAY_SESSION_END < t < self.NIGHT_SESSION_START:
            next_open = datetime.combine(now.date(), self.NIGHT_SESSION_START)
            return (next_open - now).total_seconds()

        # å¤çç»æåå°æ¬¡æ¥æ©ç
        if t > self.NIGHT_SESSION_END:
            next_open = datetime.combine(
                now.date() + timedelta(days=1),
                self.DAY_SESSION_START,
            )
            return (next_open - now).total_seconds()

        # å½åå¨äº¤ææ¶é´å
        return 0.0

    def is_preheat_time(self, dt: Optional[datetime] = None, preheat_seconds: float = 300.0) -> bool:
        """å¤æ­æ¯å¦ä¸ºå¼çåé¢ç­æ¶æ®µã?""
        now = dt or datetime.now()
        seconds_to_open = self.seconds_to_next_open(now)
        return 0 < seconds_to_open <= preheat_seconds


# ---------------------------------------------------------------------------
# æ£æ¥ç¹æä¹å?# ---------------------------------------------------------------------------

@dataclass
class LoopCheckpoint:
    """ä¸»å¾ªç¯æ£æ¥ç¹"""

    state: LoopState
    last_tick_at: Optional[datetime] = None
    last_successful_tick_at: Optional[datetime] = None
    consecutive_errors: int = 0
    total_ticks: int = 0
    total_errors: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "state": self.state.value,
            "last_tick_at": self.last_tick_at.isoformat() if self.last_tick_at else None,
            "last_successful_tick_at": self.last_successful_tick_at.isoformat() if self.last_successful_tick_at else None,
            "consecutive_errors": self.consecutive_errors,
            "total_ticks": self.total_ticks,
            "total_errors": self.total_errors,
            "metadata": self.metadata,
        }


class CheckpointStore:
    """æ£æ¥ç¹æä¹åå­å¨ã?""

    def __init__(self, path: Optional[Path] = None) -> None:
        if path is None:
            settings = get_settings()
            data_dir = Path(settings.sqlite_path).parent
            data_dir.mkdir(parents=True, exist_ok=True)
            path = data_dir / "loop_checkpoint.pkl"
        self.path = path

    def save(self, checkpoint: LoopCheckpoint) -> None:
        try:
            with open(self.path, "wb") as f:
                pickle.dump(checkpoint, f)
        except Exception as e:
            logger.warning(f"æ£æ¥ç¹ä¿å­å¤±è´¥: {e}")

    def load(self) -> Optional[LoopCheckpoint]:
        if not self.path.exists():
            return None
        try:
            with open(self.path, "rb") as f:
                return pickle.load(f)
        except Exception as e:
            logger.warning(f"æ£æ¥ç¹å è½½å¤±è´¥: {e}")
            return None

    def clear(self) -> None:
        if self.path.exists():
            self.path.unlink()


# ---------------------------------------------------------------------------
# æ éä¸»å¾ªç?# ---------------------------------------------------------------------------

class InfiniteLoop:
    """
    æ éä¸»å¾ªç?
    ç¹æ§ï¼
    - èªå¨è¯å«æè´§ä¼å¸/å¼çæ¶é?    - å¼çåé¢ç­é¶æ®µ
    - æ­ç¹ç»­ä¼ ï¼ä»ä¸æ¬¡ç¶ææ¢å¤ï¼
    - å¼å¸¸æ¢å¤ï¼ææ°éé¿éè¯ï¼
    """

    MAX_BACKOFF_SECONDS: float = 60.0
    BASE_BACKOFF_SECONDS: float = 1.0
    PREHEAT_SECONDS: float = 300.0
    MAX_CONSECUTIVE_ERRORS: int = 10

    def __init__(
        self,
        tick_func: Callable[..., Coroutine[Any, Any, Any]],
        calendar: Optional[TradingCalendar] = None,
        checkpoint_store: Optional[CheckpointStore] = None,
        redis_client: Optional[Any] = None,
    ) -> None:
        self.tick_func = tick_func
        self.calendar = calendar or TradingCalendar()
        self.store = checkpoint_store or CheckpointStore()
        self.redis = redis_client

        self._state = LoopState.IDLE
        self._task: Optional[asyncio.Task] = None
        self._running = False
        self._paused = False
        self._lock = asyncio.Lock()

        # ç»è®¡
        self._checkpoint = self.store.load() or LoopCheckpoint(state=LoopState.IDLE)
        self._backoff_seconds = self.BASE_BACKOFF_SECONDS

    # -----------------------------------------------------------------------
    # çå½å¨æ
    # -----------------------------------------------------------------------

    async def start(self) -> None:
        """å¯å¨ä¸»å¾ªç¯ã?""
        if self._running:
            return
        self._running = True
        self._state = LoopState.IDLE
        self._task = asyncio.create_task(self._loop())
        logger.info("æ éä¸»å¾ªç¯å·²å¯å¨")

    async def stop(self) -> None:
        """åæ­¢ä¸»å¾ªç¯ã?""
        self._running = False
        self._state = LoopState.STOPPED
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        self._save_checkpoint()
        logger.info("æ éä¸»å¾ªç¯å·²åæ­¢")

    async def pause(self) -> None:
        """æå¨æåã?""
        self._paused = True
        self._state = LoopState.PAUSED
        logger.info("ä¸»å¾ªç¯å·²æå¨æå")

    async def resume(self) -> None:
        """æå¨æ¢å¤ã?""
        self._paused = False
        self._state = LoopState.IDLE
        logger.info("ä¸»å¾ªç¯å·²æå¨æ¢å¤")

    @property
    def state(self) -> LoopState:
        return self._state

    @property
    def checkpoint(self) -> LoopCheckpoint:
        return self._checkpoint

    # -----------------------------------------------------------------------
    # ä¸»å¾ªç?    # -----------------------------------------------------------------------

    async def _loop(self) -> None:
        """ä¸»å¾ªç¯ä½ã?""
        while self._running:
            try:
                await self._tick_cycle()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(f"ä¸»å¾ªç¯å¼å¸? {e}")
                await self._handle_loop_error(e)

    async def _tick_cycle(self) -> None:
        """åæ¬¡å¾ªç¯å¨æã?""
        # æå¨æå
        if self._paused:
            self._state = LoopState.PAUSED
            await asyncio.sleep(1)
            return

        # æ£æ¥äº¤ææ¶é?        if not self.calendar.is_trading_time():
            self._state = LoopState.MARKET_CLOSED
            seconds_to_open = self.calendar.seconds_to_next_open()
            logger.info(f"ä¼å¸ä¸­ï¼è·ç¦»ä¸æ¬¡å¼ç?{seconds_to_open:.0f}s")
            await asyncio.sleep(min(seconds_to_open, 60))
            return

        # å¼çåé¢ç­
        if self.calendar.is_preheat_time(preheat_seconds=self.PREHEAT_SECONDS):
            self._state = LoopState.PREHEAT
            await self._preheat()

        # æ­£å¸¸è¿è¡
        self._state = LoopState.RUNNING
        await self._execute_tick()

    async def _preheat(self) -> None:
        """å¼çåé¢ç­ã?""
        logger.info("è¿å¥å¼çåé¢ç­é¶æ®µ")
        # å¯å¨æ­¤æ§è¡ï¼æ°æ®é¢å è½½ãè¿æ¥æ£æ¥ãç¶ææ¢å¤ç­
        await self._publish_state_event("preheat")
        await asyncio.sleep(1)

    async def _execute_tick(self) -> None:
        """æ§è¡ä¸æ¬?tickã?""
        self._checkpoint.last_tick_at = datetime.utcnow()
        self._checkpoint.total_ticks += 1

        try:
            await self.tick_func()
            self._checkpoint.last_successful_tick_at = datetime.utcnow()
            self._checkpoint.consecutive_errors = 0
            self._backoff_seconds = self.BASE_BACKOFF_SECONDS
        except Exception as e:
            self._checkpoint.consecutive_errors += 1
            self._checkpoint.total_errors += 1
            raise

        self._save_checkpoint()

    async def _handle_loop_error(self, error: Exception) -> None:
        """å¤çå¾ªç¯å¼å¸¸ï¼ææ°éé¿ï¼ã?""
        self._state = LoopState.RECOVERING

        if self._checkpoint.consecutive_errors >= self.MAX_CONSECUTIVE_ERRORS:
            logger.critical(
                f"è¿ç»­éè¯¯ {self._checkpoint.consecutive_errors} æ¬¡ï¼è¿å¥é¿ä¼ç?
            )
            await asyncio.sleep(self.MAX_BACKOFF_SECONDS * 2)
            self._checkpoint.consecutive_errors = 0
            return

        # ææ°éé?        sleep_time = min(self._backoff_seconds, self.MAX_BACKOFF_SECONDS)
        logger.warning(f"å¼å¸¸æ¢å¤ä¸­ï¼{sleep_time:.1f}s åéè¯?| éè¯¯: {error}")
        await asyncio.sleep(sleep_time)
        self._backoff_seconds *= 2

        await self._publish_state_event("recovering", error=str(error))

    # -----------------------------------------------------------------------
    # æ­ç¹ç»­ä¼ 
    # -----------------------------------------------------------------------

    def _save_checkpoint(self) -> None:
        self._checkpoint.state = self._state
        self.store.save(self._checkpoint)

    async def resume_from_checkpoint(self) -> None:
        """ä»æ£æ¥ç¹æ¢å¤ç¶æã?""
        cp = self.store.load()
        if cp is None:
            logger.info("æ åå²æ£æ¥ç¹ï¼å¨æ°å¯å?)
            return

        logger.info(
            f"ä»æ£æ¥ç¹æ¢å¤: state={cp.state.value}, "
            f"ticks={cp.total_ticks}, errors={cp.total_errors}"
        )

        # æ¢å¤ç»è®¡
        self._checkpoint = cp

        # è¥ä¸æ¬¡å¼å¸¸éåºï¼å¢å æ¢å¤æ è®°
        if cp.consecutive_errors > 0:
            logger.warning(f"ä¸æ¬¡å¼å¸¸éåºï¼è¿ç»­éè¯¯ {cp.consecutive_errors} æ¬?)
            self._backoff_seconds = min(
                self.BASE_BACKOFF_SECONDS * (2 ** min(cp.consecutive_errors, 5)),
                self.MAX_BACKOFF_SECONDS,
            )

        await self._publish_state_event("resumed_from_checkpoint", checkpoint=cp.to_dict())

    # -----------------------------------------------------------------------
    # äºä»¶åå¸
    # -----------------------------------------------------------------------

    async def _publish_state_event(self, event_type: str, **kwargs: Any) -> None:
        if self.redis is None:
            return
        try:
            event = {
                "type": event_type,
                "state": self._state.value,
                "timestamp": datetime.utcnow().isoformat(),
                "checkpoint": self._checkpoint.to_dict(),
                **kwargs,
            }
            await self.redis.publish("loop:state", json.dumps(event, ensure_ascii=False))
        except Exception as e:
            logger.warning(f"ç¶æäºä»¶åå¸å¤±è´? {e}")


# ---------------------------------------------------------------------------
# ç»åè¿è¡å¨ï¼å°å¤ä¸ªæå¡ç»åå°ä¸»å¾ªç¯ä¸­ï¼?# ---------------------------------------------------------------------------

class CompositeTickRunner:
    """
    ç»å Tick è¿è¡å?
    å°å¤ä¸ªå­æå¡ç?tick æ¹æ³ç»åæä¸ä¸ªä¸»å¾ªç¯ tickã?    """

    def __init__(self) -> None:
        self._handlers: List[Callable[..., Coroutine[Any, Any, Any]]] = []
        self._names: List[str] = []

    def register(
        self,
        handler: Callable[..., Coroutine[Any, Any, Any]],
        name: str = "",
    ) -> None:
        """æ³¨åä¸ä¸?tick å¤çå¨ã?""
        self._handlers.append(handler)
        self._names.append(name or handler.__name__)
        logger.info(f"Tickå¤çå¨å·²æ³¨å: {name}")

    def unregister(self, name: str) -> bool:
        """æ³¨éå¤çå¨ã?""
        if name in self._names:
            idx = self._names.index(name)
            self._handlers.pop(idx)
            self._names.pop(idx)
            return True
        return False

    async def tick(self) -> None:
        """æ§è¡æææ³¨åçå¤çå¨ç tickã?""
        for name, handler in zip(self._names, self._handlers):
            try:
                await handler()
            except Exception as e:
                logger.exception(f"[{name}] Tickæ§è¡å¤±è´¥: {e}")
                raise

    @property
    def handler_count(self) -> int:
        return len(self._handlers)
