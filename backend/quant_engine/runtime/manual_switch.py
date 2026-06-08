"""
åç§æå¨å¼å³æ§å¶å¨ â?Task 11

æ¯æä¸æï¼OFF / PAPER / LIVE
LIVEåæ¢åæ§è¡?é¡¹èªæ£ï¼åæ¢åç­ç¥Pauseï¼ä»ä½å¯é?å¹³ä»"æ?ä¿æ"ã?
æ¾ç¤ºå½åç­ç¥è¿?0æ¥å¤æ®åæå¤§åæ¤ï¼LIVEåæ¢éäºæ¬¡ç¡®è®¤ã?
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from app.config import get_settings
from app.models import (
    Candidate,
    CandidateStatus,
    SymbolMode,
    SymbolSwitch,
)
from core.candidate_core import CandidateStateMachine
from runtime.execution_gateway import ExecutionGateway
from runtime.risk_monitor import RiskMonitor
from strategy.position_lifecycle import PositionLifecycleManager

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# æä¸¾ä¸å¸¸é?
# ---------------------------------------------------------------------------

class SwitchAction(str, Enum):
    CLOSE_POSITIONS = "CLOSE_POSITIONS"
    KEEP_POSITIONS = "KEEP_POSITIONS"


class SelfCheckItem(str, Enum):
    HAS_DEPLOYABLE = "has_deployable"
    MARGIN_SUFFICIENT = "margin_sufficient"
    TQSDK_CONNECTED = "tqsdk_connected"
    NO_CIRCUIT_BREAKER = "no_circuit_breaker"
    NOT_DELIVERY_MONTH = "not_delivery_month"


LIVE_REQUIRED_CHECKS: List[SelfCheckItem] = [
    SelfCheckItem.HAS_DEPLOYABLE,
    SelfCheckItem.MARGIN_SUFFICIENT,
    SelfCheckItem.TQSDK_CONNECTED,
    SelfCheckItem.NO_CIRCUIT_BREAKER,
    SelfCheckItem.NOT_DELIVERY_MONTH,
]


# ---------------------------------------------------------------------------
# æ°æ®æ¨¡å
# ---------------------------------------------------------------------------

@dataclass
class SelfCheckResult:
    item: SelfCheckItem
    passed: bool
    message: str
    detail: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "item": self.item.value,
            "passed": self.passed,
            "message": self.message,
            "detail": self.detail,
        }


@dataclass
class SwitchPreview:
    symbol: str
    target_mode: SymbolMode
    current_mode: SymbolMode
    current_candidate: Optional[Candidate]
    paper_candidate: Optional[Candidate]
    sharpe_20d: Optional[float]
    max_drawdown_20d: Optional[float]
    self_checks: List[SelfCheckResult] = field(default_factory=list)
    all_checks_passed: bool = False
    position_action_options: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "target_mode": self.target_mode.value,
            "current_mode": self.current_mode.value,
            "current_candidate_id": self.current_candidate.id if self.current_candidate else None,
            "paper_candidate_id": self.paper_candidate.id if self.paper_candidate else None,
            "sharpe_20d": self.sharpe_20d,
            "max_drawdown_20d": self.max_drawdown_20d,
            "self_checks": [c.to_dict() for c in self.self_checks],
            "all_checks_passed": self.all_checks_passed,
            "position_action_options": self.position_action_options,
        }


@dataclass
class SwitchRecord:
    symbol: str
    from_mode: SymbolMode
    to_mode: SymbolMode
    position_action: SwitchAction
    operator: str
    confirmed: bool = False
    confirmed_at: Optional[datetime] = None
    self_check_results: List[SelfCheckResult] = field(default_factory=list)
    reason: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "from_mode": self.from_mode.value,
            "to_mode": self.to_mode.value,
            "position_action": self.position_action.value,
            "operator": self.operator,
            "confirmed": self.confirmed,
            "confirmed_at": self.confirmed_at.isoformat() if self.confirmed_at else None,
            "self_checks": [c.to_dict() for c in self.self_check_results],
            "reason": self.reason,
            "created_at": self.created_at.isoformat(),
        }


# ---------------------------------------------------------------------------
# æå¨å¼å³æ§å¶å¨
# ---------------------------------------------------------------------------

class ManualSwitchController:
    """
    åç§æå¨å¼å³æ§å¶å¨

    èè´£ï¼?
    - ç®¡çåç§ OFF / PAPER / LIVE ä¸æåæ?
    - LIVEåæ¢åæ§è¡?é¡¹èªæ£
    - åæ¢åæåç­ç¥ï¼å¤çä»ä½
    - æä¾ç­ç¥è¿?0æ¥ç»©æé¢è§?
    - LIVEåæ¢éäºæ¬¡ç¡®è®¤
    """

    MARGIN_SUFFICIENT_RATIO: float = 0.75
    DELIVERY_MONTH_DAYS: int = 15
    SHARPE_LOOKBACK_DAYS: int = 20

    def __init__(
        self,
        state_machine: CandidateStateMachine,
        risk_monitor: RiskMonitor,
        gateway: ExecutionGateway,
        position_manager: PositionLifecycleManager,
        redis_client: Optional[Any] = None,
    ) -> None:
        self.sm = state_machine
        self.risk = risk_monitor
        self.gateway = gateway
        self.pm = position_manager
        self.redis = redis_client
        self._lock = asyncio.Lock()
        self._pending_confirmations: Dict[str, SwitchRecord] = {}

    # -----------------------------------------------------------------------
    # å¬å¼API
    # -----------------------------------------------------------------------

    async def preview_switch(
        self,
        symbol_switch: SymbolSwitch,
        target_mode: SymbolMode,
        db_session: Optional[Any] = None,
    ) -> SwitchPreview:
        """
        é¢è§åæ¢ç»æï¼ä¸æ§è¡åæ¢ï¼ã?

        è¿åå½åç­ç¥ç»©æãèªæ£ç»æãå¯éæä½ã?
        """
        current_mode = symbol_switch.mode

        # è·åå³èåé?
        current_candidate = symbol_switch.current_candidate
        paper_candidate = symbol_switch.paper_candidate

        # è®¡ç®è¿?0æ¥ç»©æ?
        sharpe_20d, max_dd_20d = self._calc_recent_performance(current_candidate)

        preview = SwitchPreview(
            symbol=symbol_switch.symbol,
            target_mode=target_mode,
            current_mode=current_mode,
            current_candidate=current_candidate,
            paper_candidate=paper_candidate,
            sharpe_20d=sharpe_20d,
            max_drawdown_20d=max_dd_20d,
        )

        # LIVEåæ¢éèªæ£
        if target_mode == SymbolMode.LIVE:
            checks = await self._run_self_checks(
                symbol_switch.symbol,
                current_candidate,
                paper_candidate,
            )
            preview.self_checks = checks
            preview.all_checks_passed = all(c.passed for c in checks)
            preview.position_action_options = [
                SwitchAction.CLOSE_POSITIONS.value,
                SwitchAction.KEEP_POSITIONS.value,
            ]
        else:
            preview.all_checks_passed = True
            preview.position_action_options = [SwitchAction.CLOSE_POSITIONS.value]

        return preview

    async def request_switch(
        self,
        symbol_switch: SymbolSwitch,
        target_mode: SymbolMode,
        position_action: SwitchAction,
        operator: str,
        db_session: Optional[Any] = None,
    ) -> Tuple[bool, str, Optional[SwitchRecord]]:
        """
        è¯·æ±åæ¢åç§æ¨¡å¼ã?

        è¥ç®æ ä¸ºLIVEï¼åçæé¢è§å¹¶ç¼å­ï¼ç­å¾äºæ¬¡ç¡®è®¤ã?
        å¶ä»æ¨¡å¼ç´æ¥æ§è¡ã?
        """
        async with self._lock:
            preview = await self.preview_switch(symbol_switch, target_mode, db_session)

            if target_mode == SymbolMode.LIVE:
                if not preview.all_checks_passed:
                    failed = [c.item.value for c in preview.self_checks if not c.passed]
                    return False, f"LIVEèªæ£æªéè¿: {', '.join(failed)}", None

                # éè¦äºæ¬¡ç¡®è®?
                record = SwitchRecord(
                    symbol=symbol_switch.symbol,
                    from_mode=symbol_switch.mode,
                    to_mode=target_mode,
                    position_action=position_action,
                    operator=operator,
                    self_check_results=preview.self_checks,
                    reason="ç­å¾äºæ¬¡ç¡®è®¤",
                )
                self._pending_confirmations[symbol_switch.symbol] = record
                return (
                    True,
                    "LIVEåæ¢éäºæ¬¡ç¡®è®¤ï¼è¯·è°ç¨ confirm_switch å®æ",
                    record,
                )

            # OFF / PAPER ç´æ¥æ§è¡
            ok, msg = await self._execute_switch(
                symbol_switch=symbol_switch,
                target_mode=target_mode,
                position_action=position_action,
                operator=operator,
                db_session=db_session,
            )
            return ok, msg, None

    async def confirm_switch(
        self,
        symbol_switch: SymbolSwitch,
        operator: str,
        db_session: Optional[Any] = None,
    ) -> Tuple[bool, str]:
        """
        äºæ¬¡ç¡®è®¤LIVEåæ¢ã?
        """
        async with self._lock:
            record = self._pending_confirmations.pop(symbol_switch.symbol, None)
            if record is None:
                return False, "æ å¾ç¡®è®¤çLIVEåæ¢è¯·æ±ï¼è¯·åè°ç?request_switch"

            if record.to_mode != SymbolMode.LIVE:
                return False, "å¾ç¡®è®¤è®°å½ä¸æ¯LIVEåæ¢"

            record.confirmed = True
            record.confirmed_at = datetime.utcnow()

            ok, msg = await self._execute_switch(
                symbol_switch=symbol_switch,
                target_mode=SymbolMode.LIVE,
                position_action=record.position_action,
                operator=operator,
                db_session=db_session,
                confirmed_record=record,
            )
            return ok, msg

    async def cancel_pending(self, symbol: str) -> bool:
        """åæ¶å¾ç¡®è®¤çåæ¢è¯·æ±ã?""
        async with self._lock:
            return self._pending_confirmations.pop(symbol, None) is not None

    def get_pending_confirmation(self, symbol: str) -> Optional[SwitchRecord]:
        """è·åå¾ç¡®è®¤çåæ¢è®°å½ã?""
        return self._pending_confirmations.get(symbol)

    # -----------------------------------------------------------------------
    # èªæ£é»è¾
    # -----------------------------------------------------------------------

    async def _run_self_checks(
        self,
        symbol: str,
        current_candidate: Optional[Candidate],
        paper_candidate: Optional[Candidate],
    ) -> List[SelfCheckResult]:
        checks = []
        for item in LIVE_REQUIRED_CHECKS:
            result = await self._check_item(item, symbol, current_candidate, paper_candidate)
            checks.append(result)
        return checks

    async def _check_item(
        self,
        item: SelfCheckItem,
        symbol: str,
        current_candidate: Optional[Candidate],
        paper_candidate: Optional[Candidate],
    ) -> SelfCheckResult:
        if item == SelfCheckItem.HAS_DEPLOYABLE:
            return self._check_has_deployable(current_candidate, paper_candidate)
        elif item == SelfCheckItem.MARGIN_SUFFICIENT:
            return self._check_margin_sufficient(symbol)
        elif item == SelfCheckItem.TQSDK_CONNECTED:
            return await self._check_tqsdk_connected()
        elif item == SelfCheckItem.NO_CIRCUIT_BREAKER:
            return self._check_no_circuit_breaker()
        elif item == SelfCheckItem.NOT_DELIVERY_MONTH:
            return self._check_not_delivery_month(symbol)
        return SelfCheckResult(item, False, "æªç¥æ£æ¥é¡¹")

    def _check_has_deployable(
        self,
        current_candidate: Optional[Candidate],
        paper_candidate: Optional[Candidate],
    ) -> SelfCheckResult:
        has_deployable = False
        candidate_id = None
        if current_candidate and current_candidate.status in (
            CandidateStatus.DEPLOYABLE,
            CandidateStatus.RUNNING,
        ):
            has_deployable = True
            candidate_id = current_candidate.id
        elif paper_candidate and paper_candidate.status in (
            CandidateStatus.DEPLOYABLE,
            CandidateStatus.PAPER,
        ):
            has_deployable = True
            candidate_id = paper_candidate.id

        return SelfCheckResult(
            item=SelfCheckItem.HAS_DEPLOYABLE,
            passed=has_deployable,
            message="å­å¨å¯é¨ç½²ç­ç? if has_deployable else "æ Deployable/Paper/Runningç­ç¥",
            detail={"candidate_id": candidate_id},
        )

    def _check_margin_sufficient(self, symbol: str) -> SelfCheckResult:
        margin_total = self.risk._margin_total
        margin_used = self.risk._margin_used
        ratio = float(margin_used) / float(margin_total) if margin_total > 0 else 0.0
        passed = ratio < self.MARGIN_SUFFICIENT_RATIO
        return SelfCheckResult(
            item=SelfCheckItem.MARGIN_SUFFICIENT,
            passed=passed,
            message=f"ä¿è¯éå ç¨ç {ratio:.2%} {'åè¶³' if passed else 'ä¸è¶³'}",
            detail={"ratio": ratio, "used": float(margin_used), "total": float(margin_total)},
        )

    async def _check_tqsdk_connected(self) -> SelfCheckResult:
        connected = await self.gateway.adapter.connect()
        return SelfCheckResult(
            item=SelfCheckItem.TQSDK_CONNECTED,
            passed=connected,
            message="å¤©å¤è¿æ¥æ­£å¸¸" if connected else "å¤©å¤è¿æ¥å¤±è´¥",
            detail={"sim": get_settings().tqsdk_sim},
        )

    def _check_no_circuit_breaker(self) -> SelfCheckResult:
        active = self.risk.is_circuit_breaker_active
        return SelfCheckResult(
            item=SelfCheckItem.NO_CIRCUIT_BREAKER,
            passed=not active,
            message="å½æ¥æªçæ? if not active else "å½æ¥å·²çæ?,
            detail={"circuit_breaker_active": active},
        )

    def _check_not_delivery_month(self, symbol: str) -> SelfCheckResult:
        now = datetime.utcnow()
        is_delivery = False
        days_to_delivery = None
        if len(symbol) >= 6:
            try:
                contract_month = int(symbol[-4:-2])
                contract_year = int(symbol[-6:-4]) + 2000
                contract_date = datetime(contract_year, contract_month, 15)
                days_to_delivery = (contract_date - now).days
                is_delivery = 0 < days_to_delivery <= self.DELIVERY_MONTH_DAYS
            except (ValueError, IndexError):
                pass

        passed = not is_delivery
        return SelfCheckResult(
            item=SelfCheckItem.NOT_DELIVERY_MONTH,
            passed=passed,
            message=f"è·äº¤å²æ {days_to_delivery} å¤©ï¼{'å¨äº¤å²æå? if is_delivery else 'å®å¨'}"
            if days_to_delivery is not None
            else "æ æ³å¤æ­äº¤å²æ?,
            detail={"days_to_delivery": days_to_delivery},
        )

    # -----------------------------------------------------------------------
    # åæ¢æ§è¡
    # -----------------------------------------------------------------------

    async def _execute_switch(
        self,
        symbol_switch: SymbolSwitch,
        target_mode: SymbolMode,
        position_action: SwitchAction,
        operator: str,
        db_session: Optional[Any] = None,
        confirmed_record: Optional[SwitchRecord] = None,
    ) -> Tuple[bool, str]:
        symbol = symbol_switch.symbol
        from_mode = symbol_switch.mode

        logger.info(
            f"[{symbol}] å¼å§æ¨¡å¼åæ? {from_mode.value} â?{target_mode.value} | "
            f"ä»ä½å¤ç={position_action.value} | æä½äº?{operator}"
        )

        # 1. æåå½åç­ç¥
        await self._pause_current_strategy(symbol_switch, db_session)

        # 2. å¤çä»ä½
        if position_action == SwitchAction.CLOSE_POSITIONS:
            closed = await self._close_all_positions(symbol)
            logger.info(f"[{symbol}] å·²å¹³ä»?{len(closed)} ä¸ªä»ä½?)
        else:
            logger.info(f"[{symbol}] ä¿æç°æä»ä½")

        # 3. æ´æ°SymbolSwitchæ¨¡å¼
        symbol_switch.mode = target_mode
        symbol_switch.last_switch_at = datetime.utcnow()
        symbol_switch.switch_reason = (
            confirmed_record.reason if confirmed_record else f"æå¨åæ¢ {from_mode.value}â{target_mode.value}"
        )
        symbol_switch.operator = operator

        if target_mode == SymbolMode.LIVE:
            symbol_switch.live_enabled_at = datetime.utcnow()

        if db_session is not None:
            await db_session.commit()

        # 4. åå¸äºä»¶
        event = {
            "type": "symbol_mode_switch",
            "symbol": symbol,
            "from_mode": from_mode.value,
            "to_mode": target_mode.value,
            "position_action": position_action.value,
            "operator": operator,
            "timestamp": datetime.utcnow().isoformat(),
        }
        await self._publish_event(event)

        msg = f"[{symbol}] åæ¢å®æ: {from_mode.value} â?{target_mode.value}"
        logger.info(msg)
        return True, msg

    async def _pause_current_strategy(
        self,
        symbol_switch: SymbolSwitch,
        db_session: Optional[Any] = None,
    ) -> None:
        """æåå½ååç§å³èçç­ç¥ã?""
        candidates_to_pause: List[Candidate] = []
        if symbol_switch.current_candidate:
            candidates_to_pause.append(symbol_switch.current_candidate)
        if symbol_switch.paper_candidate:
            candidates_to_pause.append(symbol_switch.paper_candidate)

        for candidate in candidates_to_pause:
            if candidate.status == CandidateStatus.RUNNING:
                await self.sm.transition(
                    candidate=candidate,
                    target_status=CandidateStatus.DEGRADED,
                    reason=f"åç§ {symbol_switch.symbol} æ¨¡å¼åæ¢ï¼ç­ç¥æå?,
                    db_session=db_session,
                    metadata={"symbol": symbol_switch.symbol, "action": "pause_on_switch"},
                )
                logger.info(f"[{symbol_switch.symbol}] ç­ç¥ {candidate.id} å·²æå?)

    async def _close_all_positions(self, symbol: str) -> List[Tuple[str, Decimal]]:
        """å¹³ä»æå®åç§çææä»ä½ã?""
        from strategy.spec import PositionIntent, SignalDirection, PositionAction
        import pandas as pd

        positions = self.pm.get_symbol_positions(symbol, only_open=True)
        results = []
        for pos in positions:
            intent = PositionIntent(
                candidate_id=pos.candidate_id,
                symbol=pos.symbol,
                target_direction=SignalDirection.FLAT,
                target_lots=pos.lots,
                action=PositionAction.CLOSE,
                timestamp=pd.Timestamp.now(),
                reason="åç§æ¨¡å¼åæ¢èªå¨å¹³ä»",
                urgency="urgent",
            )
            try:
                order_result = await self.gateway.submit_order(intent)
                if order_result.filled_price:
                    closed_pos, pnl = self.pm.close_position(
                        pos.id,
                        order_result.filled_price,
                        datetime.utcnow(),
                        reason="åç§æ¨¡å¼åæ¢èªå¨å¹³ä»",
                    )
                    results.append((pos.id, pnl))
            except Exception as e:
                logger.exception(f"[{symbol}] å¹³ä»å¤±è´¥ {pos.id}: {e}")
        return results

    # -----------------------------------------------------------------------
    # ç»©æè®¡ç®
    # -----------------------------------------------------------------------

    def _calc_recent_performance(
        self,
        candidate: Optional[Candidate],
    ) -> Tuple[Optional[float], Optional[float]]:
        """
        è®¡ç®åéç­ç¥è¿20æ¥å¤æ®åæå¤§åæ¤ã?

        ç®åå®ç°ï¼ä¼åä½¿ç¨å·²æå­æ®µï¼è¥ä¸å­å¨åè¿åNoneã?
        å®éå¯æ¥å¥åæµå¼æè®¡ç®ã?
        """
        if candidate is None:
            return None, None

        sharpe = candidate.sharpe_paper_5d
        max_dd = candidate.max_drawdown

        # è¥sharpe_paper_5dä¸å­å¨ï¼å°è¯ç¨test sharpeä½ä¸ºè¿ä¼¼
        if sharpe is None:
            sharpe = candidate.sharpe_test

        return sharpe, max_dd

    # -----------------------------------------------------------------------
    # äºä»¶åå¸
    # -----------------------------------------------------------------------

    async def _publish_event(self, event: Dict[str, Any]) -> None:
        if self.redis is None:
            return
        try:
            await self.redis.publish("symbol:switch", json.dumps(event, ensure_ascii=False))
        except Exception as e:
            logger.warning(f"åæ¢äºä»¶åå¸å¤±è´¥: {e}")


# ---------------------------------------------------------------------------
# æ¹éå¼å³ç®¡ç?
# ---------------------------------------------------------------------------

class BatchSwitchManager:
    """æ¹éåç§å¼å³ç®¡çå¨ã?""

    def __init__(self, controller: ManualSwitchController) -> None:
        self.controller = controller

    async def batch_switch(
        self,
        switches: List[SymbolSwitch],
        target_mode: SymbolMode,
        position_action: SwitchAction,
        operator: str,
        db_session: Optional[Any] = None,
    ) -> List[Tuple[str, bool, str]]:
        """æ¹éåæ¢åç§æ¨¡å¼ã?""
        results = []
        for sw in switches:
            try:
                ok, msg, _ = await self.controller.request_switch(
                    sw, target_mode, position_action, operator, db_session
                )
                results.append((sw.symbol, ok, msg))
            except Exception as e:
                logger.exception(f"[{sw.symbol}] æ¹éåæ¢å¼å¸¸: {e}")
                results.append((sw.symbol, False, str(e)))
        return results

    async def emergency_stop_all(
        self,
        switches: List[SymbolSwitch],
        operator: str,
        db_session: Optional[Any] = None,
    ) -> List[Tuple[str, bool, str]]:
        """ç´§æ¥åæ­¢ææåç§ï¼åæ¢å°OFFå¹¶å¹³ä»ï¼ã?""
        results = []
        for sw in switches:
            if sw.mode == SymbolMode.OFF:
                results.append((sw.symbol, True, "å·²æ¯OFFç¶æ?))
                continue
            try:
                ok, msg, _ = await self.controller.request_switch(
                    sw, SymbolMode.OFF, SwitchAction.CLOSE_POSITIONS, operator, db_session
                )
                results.append((sw.symbol, ok, msg))
            except Exception as e:
                logger.exception(f"[{sw.symbol}] ç´§æ¥åæ­¢å¼å¸? {e}")
                results.append((sw.symbol, False, str(e)))
        return results
