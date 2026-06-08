"""
ç­ç¥è¿è¡å?â?ç­ç¥ä¿¡å·çæä¸æ§è¡ç¼æ?

æ ¸å¿è½åï¼?
- å¼æ­¥è¿è¡å¤ä¸ªç­ç¥
- ä¿¡å·çæ â?é£æ§æ£æ?â?æ§è¡ä¸å
- ä¸ç¶ææºãé£æ§ãæ§è¡ç½å³èå?
- æ¯ææ¨¡æç?å®çåæ¢
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from app.models import Candidate, CandidateStatus
from core.candidate_core import CandidateStateMachine
from runtime.execution_gateway import ExecutionGateway, OrderResult
from runtime.risk_monitor import RiskMonitor
from strategy.position_lifecycle import PositionLifecycleManager
from strategy.spec import PositionIntent, Signal, SignalDirection

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# è¿è¡ç»æ
# ---------------------------------------------------------------------------

@dataclass
class RunResult:
    """åæ¬¡è¿è¡ç»æ"""

    candidate_id: str
    symbol: str
    signal_generated: bool = False
    signal: Optional[Signal] = None
    risk_blocked: bool = False
    risk_reason: str = ""
    order_submitted: bool = False
    order_result: Optional[OrderResult] = None
    position_updated: bool = False
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "symbol": self.symbol,
            "signal_generated": self.signal_generated,
            "signal": self.signal.to_dict() if self.signal else None,
            "risk_blocked": self.risk_blocked,
            "risk_reason": self.risk_reason,
            "order_submitted": self.order_submitted,
            "order_result": self.order_result.to_dict() if self.order_result else None,
            "position_updated": self.position_updated,
            "timestamp": self.timestamp.isoformat(),
        }


# ---------------------------------------------------------------------------
# ç­ç¥è¿è¡å?
# ---------------------------------------------------------------------------

class StrategyRunner:
    """
    ç­ç¥è¿è¡å?

    ç¼æç­ç¥çå®æ´æ§è¡æµç¨ï¼
    1. ä¿¡å·çæ
    2. é£æ§æ£æ?
    3. ä»ä½è®¡ç®
    4. æ§è¡ä¸å
    5. ä»ä½æ´æ°
    """

    def __init__(
        self,
        gateway: ExecutionGateway,
        risk_monitor: RiskMonitor,
        position_manager: PositionLifecycleManager,
        state_machine: Optional[CandidateStateMachine] = None,
        redis_client: Optional[Any] = None,
    ) -> None:
        self.gateway = gateway
        self.risk = risk_monitor
        self.pm = position_manager
        self.sm = state_machine or CandidateStateMachine(redis_client)
        self.redis = redis_client
        self._running = False
        self._tasks: Dict[str, asyncio.Task] = {}

    async def start(self) -> None:
        """å¯å¨è¿è¡å¨ã?""
        self._running = True
        logger.info("ç­ç¥è¿è¡å¨å·²å¯å¨")

    async def stop(self) -> None:
        """åæ­¢è¿è¡å¨ã?""
        self._running = False
        for task in self._tasks.values():
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks.values(), return_exceptions=True)
        self._tasks.clear()
        logger.info("ç­ç¥è¿è¡å¨å·²åæ­¢")

    async def run_candidate(
        self,
        candidate: Candidate,
        data: pd.DataFrame,
        factor_values: Optional[Any] = None,
        is_paper: bool = True,
    ) -> RunResult:
        """
        è¿è¡åä¸ªåéç­ç¥ã?

        Parameters
        ----------
        candidate : Candidate
            åéç­ç?
        data : pd.DataFrame
            å¸åºæ°æ®
        factor_values : np.ndarray, optional
            å å­å?
        is_paper : bool
            æ¯å¦æ¨¡æç?

        Returns
        -------
        RunResult
        """
        result = RunResult(
            candidate_id=candidate.id,
            symbol=candidate.symbol,
        )

        if not self._running:
            result.risk_blocked = True
            result.risk_reason = "è¿è¡å¨æªå¯å¨"
            return result

        # æ£æ¥åéç¶æ?
        if candidate.status not in (CandidateStatus.RUNNING, CandidateStatus.PAPER):
            result.risk_blocked = True
            result.risk_reason = f"åéç¶æä¸º {candidate.status.value}ï¼ä¸æ§è¡äº¤æ"
            return result

        # é£æ§æ£æ¥ï¼åç§æå
        if self.risk.is_symbol_paused(candidate.symbol):
            result.risk_blocked = True
            result.risk_reason = f"åç§ {candidate.symbol} å·²è¢«é£æ§æå"
            return result

        # é£æ§æ£æ¥ï¼åéæå?
        if self.risk.is_candidate_paused(candidate.id):
            result.risk_blocked = True
            result.risk_reason = f"åé?{candidate.id} å·²è¢«é£æ§æå"
            return result

        # é£æ§æ£æ¥ï¼å¨ç³»ç»çæ?
        if self.risk.is_circuit_breaker_active:
            result.risk_blocked = True
            result.risk_reason = "å¨ç³»ç»çæ­ä¸­"
            return result

        # é£æ§æ£æ¥ï¼æ§è¡ç½å³çæ­
        if self.gateway.is_circuit_open:
            result.risk_blocked = True
            result.risk_reason = "æ§è¡ç½å³çæ­ä¸?
            return result

        # 1. ä¿¡å·çæï¼ç®åå®ç°ï¼å®éåºè°ç¨ç­ç¥å¬å¼è®¡ç®ï¼
        signal = self._generate_signal(candidate, data, factor_values)
        result.signal_generated = signal is not None
        result.signal = signal

        if signal is None or signal.direction == SignalDirection.FLAT:
            return result

        # 2. ä»ä½è®¡ç®
        current_positions = self.pm.get_candidate_positions(candidate.id, only_open=True)
        current_lots = sum(p.lots for p in current_positions)
        current_direction = SignalDirection.FLAT
        if current_positions:
            current_direction = SignalDirection.LONG if current_positions[0].is_long else SignalDirection.SHORT

        intent = self._calculate_position_intent(
            candidate=candidate,
            signal=signal,
            current_lots=current_lots,
            current_direction=current_direction,
        )

        if intent is None or intent.action.value == "HOLD":
            return result

        # 3. æ§è¡ä¸å
        try:
            order_result = await self.gateway.submit_order(
                intent=intent,
                price_type="LIMIT",
                limit_price=Decimal(str(data["close"].iloc[-1])) if not data.empty else None,
            )
            result.order_submitted = True
            result.order_result = order_result

            # æ´æ°é£æ§çäº
            if order_result.filled_price and order_result.filled_volume > 0:
                self._update_pnl_on_fill(candidate.symbol, candidate.id, intent, order_result)

            # 4. æ´æ°ä»ä½
            if order_result.status.value in ("FILLED", "PARTIAL_FILLED"):
                position_id = f"POS-{uuid.uuid4().hex[:12].upper()}"
                self.pm.open_position(
                    position_id=position_id,
                    intent=intent,
                    entry_price=order_result.filled_price or Decimal(str(data["close"].iloc[-1])),
                    order_id=order_result.exchange_order_id,
                    is_paper=is_paper,
                )
                result.position_updated = True

        except Exception as e:
            logger.exception(f"[{candidate.symbol}] ä¸åå¼å¸¸: {e}")
            result.risk_blocked = True
            result.risk_reason = f"ä¸åå¼å¸¸: {e}"

        return result

    def _generate_signal(
        self,
        candidate: Candidate,
        data: pd.DataFrame,
        factor_values: Optional[Any] = None,
    ) -> Optional[Signal]:
        """çæäº¤æä¿¡å·ã?""
        if data.empty:
            return None

        last_close = data["close"].iloc[-1]
        timestamp = data.index[-1] if isinstance(data.index[-1], pd.Timestamp) else pd.Timestamp.now()

        # ç®åå®ç°ï¼åºäºå å­å¼å¤æ?
        # å®éåºæ ¹æ®candidate.formulaè®¡ç®å å­å?
        if factor_values is not None and len(factor_values) > 0:
            factor_value = factor_values[-1]
        else:
            factor_value = 0.0

        direction = SignalDirection.FLAT
        if factor_value > 0.5:
            direction = SignalDirection.LONG
        elif factor_value < -0.5:
            direction = SignalDirection.SHORT

        if direction == SignalDirection.FLAT:
            return None

        return Signal(
            candidate_id=candidate.id,
            symbol=candidate.symbol,
            direction=direction,
            strength=min(abs(factor_value), 1.0),
            timestamp=timestamp,
        )

    def _calculate_position_intent(
        self,
        candidate: Candidate,
        signal: Signal,
        current_lots: int,
        current_direction: SignalDirection,
    ) -> Optional[PositionIntent]:
        """è®¡ç®ä»ä½æå¾ã?""
        from strategy.spec import PositionAction

        timestamp = signal.timestamp if hasattr(signal, "timestamp") else pd.Timestamp.now()

        # æ æä»æ¶å¼ä»?
        if current_lots == 0:
            if signal.direction == SignalDirection.FLAT:
                return None
            return PositionIntent(
                candidate_id=candidate.id,
                symbol=candidate.symbol,
                target_direction=signal.direction,
                target_lots=1,  # ç®åï¼åºå®1æ?
                action=PositionAction.OPEN,
                timestamp=timestamp,
                reason=f"ä¿¡å·è§¦å: {signal.direction.name}",
            )

        # ææä»æ¶å¤æ­æ¯å¦éè¦å¹³ä»æåæ
        if signal.direction == SignalDirection.FLAT:
            return PositionIntent(
                candidate_id=candidate.id,
                symbol=candidate.symbol,
                target_direction=current_direction,
                target_lots=current_lots,
                action=PositionAction.CLOSE,
                timestamp=timestamp,
                reason="ä¿¡å·å¹³ä»",
            )

        if signal.direction != current_direction:
            return PositionIntent(
                candidate_id=candidate.id,
                symbol=candidate.symbol,
                target_direction=signal.direction,
                target_lots=current_lots,
                action=PositionAction.REVERSE,
                timestamp=timestamp,
                reason=f"åæ: {current_direction.name} â?{signal.direction.name}",
            )

        # æ¹åä¸è´ï¼æä»ä¸å
        return PositionIntent(
            candidate_id=candidate.id,
            symbol=candidate.symbol,
            target_direction=signal.direction,
            target_lots=current_lots,
            action=PositionAction.HOLD,
            timestamp=timestamp,
            reason="æä»ä¸å",
        )

    def _update_pnl_on_fill(
        self,
        symbol: str,
        candidate_id: str,
        intent: PositionIntent,
        order_result: OrderResult,
    ) -> None:
        """æäº¤åæ´æ°çäºç»è®¡ã?""
        # æ´æ°å½æ¥çäºï¼ç®åï¼å®éåºæ ¹æ®æä»ååè®¡ç®ï¼
        # self.risk.update_daily_pnl(pnl)
        pass

    async def run_batch(
        self,
        candidates: List[Candidate],
        data_map: Dict[str, pd.DataFrame],
        factor_map: Optional[Dict[str, Any]] = None,
        is_paper: bool = True,
    ) -> List[RunResult]:
        """æ¹éè¿è¡åéç­ç¥ã?""
        tasks = []
        for c in candidates:
            data = data_map.get(c.symbol)
            if data is None:
                continue
            factors = factor_map.get(c.id) if factor_map else None
            tasks.append(self.run_candidate(c, data, factors, is_paper))

        if not tasks:
            return []

        results = await asyncio.gather(*tasks, return_exceptions=True)
        run_results: List[RunResult] = []
        for r in results:
            if isinstance(r, Exception):
                logger.error(f"ç­ç¥è¿è¡å¼å¸¸: {r}")
            else:
                run_results.append(r)
        return run_results

    async def monitor_positions(self, price_map: Dict[str, Decimal]) -> None:
        """çæ§æææªå¹³ä»ä½çç¯å¸çäºã?""
        for pos in self.pm.get_all_open_positions():
            price = price_map.get(pos.symbol)
            if price is None:
                continue

            # æ´æ°ç¯å¸çäº
            self.pm.update_position_mtm(pos.id, price)

            # æ£æ¥æ­¢æ?
            if self.pm.check_stop_loss(pos.id, price):
                logger.warning(f"[{pos.symbol}] ä»ä½ {pos.id} è§¦åæ­¢æ")
                # è§¦åæ­¢æå¹³ä»
                intent = PositionIntent(
                    candidate_id=pos.candidate_id,
                    symbol=pos.symbol,
                    target_direction=SignalDirection.FLAT,
                    target_lots=pos.lots,
                    action=PositionAction.CLOSE,
                    timestamp=pd.Timestamp.now(),
                    reason="æ­¢æè§¦å",
                    urgency="urgent",
                )
                try:
                    await self.gateway.submit_order(intent, limit_price=price)
                except Exception as e:
                    logger.exception(f"æ­¢æä¸åå¤±è´¥: {e}")

            # æ£æ¥æ­¢ç?
            if self.pm.check_take_profit(pos.id, price):
                logger.info(f"[{pos.symbol}] ä»ä½ {pos.id} è§¦åæ­¢ç")
                intent = PositionIntent(
                    candidate_id=pos.candidate_id,
                    symbol=pos.symbol,
                    target_direction=SignalDirection.FLAT,
                    target_lots=pos.lots,
                    action=PositionAction.CLOSE,
                    timestamp=pd.Timestamp.now(),
                    reason="æ­¢çè§¦å",
                )
                try:
                    await self.gateway.submit_order(intent, limit_price=price)
                except Exception as e:
                    logger.exception(f"æ­¢çä¸åå¤±è´¥: {e}")

    async def close_all_positions(
        self,
        symbol: Optional[str] = None,
        candidate_id: Optional[str] = None,
        reason: str = "",
    ) -> List[Tuple[str, Decimal]]:
        """å¹³ä»ææä»ä½ã?""
        if candidate_id:
            positions = self.pm.get_candidate_positions(candidate_id, only_open=True)
        elif symbol:
            positions = self.pm.get_symbol_positions(symbol, only_open=True)
        else:
            positions = self.pm.get_all_open_positions()

        results = []
        for pos in positions:
            intent = PositionIntent(
                candidate_id=pos.candidate_id,
                symbol=pos.symbol,
                target_direction=SignalDirection.FLAT,
                target_lots=pos.lots,
                action=PositionAction.CLOSE,
                timestamp=pd.Timestamp.now(),
                reason=reason or "æ¹éå¹³ä»",
            )
            try:
                order_result = await self.gateway.submit_order(intent)
                if order_result.filled_price:
                    closed_pos, pnl = self.pm.close_position(
                        pos.id,
                        order_result.filled_price,
                        datetime.utcnow(),
                        reason=reason or "æ¹éå¹³ä»",
                    )
                    results.append((pos.id, pnl))
            except Exception as e:
                logger.exception(f"å¹³ä»å¤±è´¥ {pos.id}: {e}")

        return results
