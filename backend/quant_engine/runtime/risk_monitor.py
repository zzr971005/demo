"""
å®æ¶é£æ§çæ§

çæ§é¡¹ï¼
- ååç§åæ?10%èªå¨æå
- åæ¥äºæ>5%å¨ç³»ç»çæ?- ä¿è¯éå®æ¶çæ?- äº¤å²æè­¦å?- é£æ§è§åå¯éç½?"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from app.config import get_settings
from app.models import RiskEvent, RiskLevel

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# é£æ§è§åéç½®
# ---------------------------------------------------------------------------

@dataclass
class RiskRuleConfig:
    """åæ¡é£æ§è§åéç½®"""

    name: str
    enabled: bool = True
    level: RiskLevel = RiskLevel.MEDIUM
    threshold: float = 0.0
    action: str = "alert"  # alert | pause | stop | circuit_breaker
    cooldown_minutes: int = 5
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "enabled": self.enabled,
            "level": self.level.value,
            "threshold": self.threshold,
            "action": self.action,
            "cooldown_minutes": self.cooldown_minutes,
            "description": self.description,
        }


DEFAULT_RISK_RULES: List[RiskRuleConfig] = [
    RiskRuleConfig(
        name="single_symbol_drawdown",
        enabled=True,
        level=RiskLevel.HIGH,
        threshold=0.10,
        action="pause",
        cooldown_minutes=10,
        description="ååç§åæ¤è¶è¿?0%èªå¨æå",
    ),
    RiskRuleConfig(
        name="daily_loss_limit",
        enabled=True,
        level=RiskLevel.CRITICAL,
        threshold=0.05,
        action="circuit_breaker",
        cooldown_minutes=60,
        description="åæ¥äºæè¶è¿5%å¨ç³»ç»çæ?,
    ),
    RiskRuleConfig(
        name="margin_ratio",
        enabled=True,
        level=RiskLevel.HIGH,
        threshold=0.80,
        action="alert",
        cooldown_minutes=5,
        description="ä¿è¯éå ç¨çè¶è¿80%åè­¦",
    ),
    RiskRuleConfig(
        name="delivery_month_warning",
        enabled=True,
        level=RiskLevel.MEDIUM,
        threshold=15,
        action="alert",
        cooldown_minutes=1440,
        description="äº¤å²æå15å¤©è­¦å?,
    ),
    RiskRuleConfig(
        name="consecutive_loss",
        enabled=True,
        level=RiskLevel.HIGH,
        threshold=5,
        action="pause",
        cooldown_minutes=30,
        description="è¿ç»­äºæç¬æ°è¶è¿5ç¬æå?,
    ),
]


# ---------------------------------------------------------------------------
# é£æ§äºä»¶
# ---------------------------------------------------------------------------

@dataclass
class RiskAlert:
    """é£æ§åè­¦"""

    rule_name: str
    level: RiskLevel
    symbol: Optional[str]
    message: str
    metric_value: float
    metric_threshold: float
    action_taken: str
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_name": self.rule_name,
            "level": self.level.value,
            "symbol": self.symbol,
            "message": self.message,
            "metric_value": self.metric_value,
            "metric_threshold": self.metric_threshold,
            "action_taken": self.action_taken,
            "timestamp": self.timestamp.isoformat(),
        }


# ---------------------------------------------------------------------------
# é£æ§çæ§å?# ---------------------------------------------------------------------------

class RiskMonitor:
    """
    å®æ¶é£æ§çæ§å?
    æç»­çæ§äº¤æé£é©ï¼è§¦åéå¼æ¶èªå¨æ§è¡é¢è®¾å¨ä½ã?    """

    def __init__(
        self,
        redis_client: Optional[Any] = None,
        rules: Optional[List[RiskRuleConfig]] = None,
    ) -> None:
        self.redis = redis_client
        self.rules = {r.name: r for r in (rules or DEFAULT_RISK_RULES)}
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()

        # çæ§ç¶æ?        self._daily_pnl: Decimal = Decimal("0")
        self._daily_pnl_date: datetime = datetime.utcnow().date()
        self._symbol_drawdowns: Dict[str, float] = {}
        self._symbol_pnl: Dict[str, Decimal] = {}
        self._margin_used: Decimal = Decimal("0")
        self._margin_total: Decimal = Decimal("0")
        self._consecutive_losses: Dict[str, int] = {}
        self._circuit_breaker_active: bool = False
        self._paused_symbols: Set[str] = set()
        self._paused_candidates: Set[str] = set()

        # å·å´è®°å½
        self._last_triggered: Dict[str, datetime] = {}
        self._alert_history: List[RiskAlert] = []

    async def start(self, interval_seconds: float = 5.0) -> None:
        """å¯å¨çæ§å¾ªç¯ã?""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._monitor_loop(interval_seconds))
        logger.info(f"é£æ§çæ§å·²å¯å¨ï¼é´é={interval_seconds}s")

    async def stop(self) -> None:
        """åæ­¢çæ§å¾ªç¯ã?""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("é£æ§çæ§å·²åæ­?)

    async def _monitor_loop(self, interval: float) -> None:
        """çæ§ä¸»å¾ªç¯ã?""
        while self._running:
            try:
                await self.run_once()
            except Exception as e:
                logger.exception(f"é£æ§çæ§å¼å¸¸: {e}")
            await asyncio.sleep(interval)

    async def run_once(self) -> List[RiskAlert]:
        """æ§è¡ä¸æ¬¡å®æ´é£æ§æ£æ¥ã?""
        alerts: List[RiskAlert] = []

        # æ£æ¥åæ¥äºæ?        alert = await self._check_daily_loss()
        if alert:
            alerts.append(alert)

        # æ£æ¥ååç§åæ¤
        for symbol, dd in list(self._symbol_drawdowns.items()):
            alert = await self._check_symbol_drawdown(symbol, dd)
            if alert:
                alerts.append(alert)

        # æ£æ¥ä¿è¯é
        alert = await self._check_margin()
        if alert:
            alerts.append(alert)

        # æ£æ¥äº¤å²æ
        alert = await self._check_delivery_month()
        if alert:
            alerts.append(alert)

        # æ£æ¥è¿ç»­äºæ?        for candidate_id, count in list(self._consecutive_losses.items()):
            alert = await self._check_consecutive_loss(candidate_id, count)
            if alert:
                alerts.append(alert)

        return alerts

    async def _check_daily_loss(self) -> Optional[RiskAlert]:
        """æ£æ¥åæ¥äºæéå¶ã?""
        rule = self.rules.get("daily_loss_limit")
        if not rule or not rule.enabled:
            return None

        today = datetime.utcnow().date()
        if today != self._daily_pnl_date:
            self._daily_pnl = Decimal("0")
            self._daily_pnl_date = today

        # åè®¾åå§èµéä¸?00ä¸ï¼è®¡ç®äºææ¯ä¾
        init_capital = Decimal("1_000_000")
        loss_ratio = abs(float(self._daily_pnl)) / float(init_capital)

        if loss_ratio < rule.threshold:
            return None

        if not self._can_trigger(rule.name, rule.cooldown_minutes):
            return None

        self._circuit_breaker_active = True
        alert = RiskAlert(
            rule_name=rule.name,
            level=rule.level,
            symbol=None,
            message=f"åæ¥äºæ {loss_ratio:.2%} è¶è¿éå?{rule.threshold:.2%}",
            metric_value=loss_ratio,
            metric_threshold=rule.threshold,
            action_taken=rule.action,
        )
        await self._handle_alert(alert)
        return alert

    async def _check_symbol_drawdown(self, symbol: str, drawdown: float) -> Optional[RiskAlert]:
        """æ£æ¥ååç§åæ¤ã?""
        rule = self.rules.get("single_symbol_drawdown")
        if not rule or not rule.enabled:
            return None

        if drawdown < rule.threshold:
            return None

        if not self._can_trigger(f"{rule.name}:{symbol}", rule.cooldown_minutes):
            return None

        self._paused_symbols.add(symbol)
        alert = RiskAlert(
            rule_name=rule.name,
            level=rule.level,
            symbol=symbol,
            message=f"åç§ {symbol} åæ¤ {drawdown:.2%} è¶è¿éå?{rule.threshold:.2%}",
            metric_value=drawdown,
            metric_threshold=rule.threshold,
            action_taken=rule.action,
        )
        await self._handle_alert(alert)
        return alert

    async def _check_margin(self) -> Optional[RiskAlert]:
        """æ£æ¥ä¿è¯éå ç¨ã?""
        rule = self.rules.get("margin_ratio")
        if not rule or not rule.enabled:
            return None

        if self._margin_total <= 0:
            return None

        margin_ratio = float(self._margin_used) / float(self._margin_total)
        if margin_ratio < rule.threshold:
            return None

        if not self._can_trigger(rule.name, rule.cooldown_minutes):
            return None

        alert = RiskAlert(
            rule_name=rule.name,
            level=rule.level,
            symbol=None,
            message=f"ä¿è¯éå ç¨ç {margin_ratio:.2%} è¶è¿éå?{rule.threshold:.2%}",
            metric_value=margin_ratio,
            metric_threshold=rule.threshold,
            action_taken=rule.action,
        )
        await self._handle_alert(alert)
        return alert

    async def _check_delivery_month(self) -> Optional[RiskAlert]:
        """æ£æ¥äº¤å²æè­¦åã?""
        rule = self.rules.get("delivery_month_warning")
        if not rule or not rule.enabled:
            return None

        now = datetime.utcnow()
        # ç®åå¤çï¼æ£æ¥å½åæä»½æ¯å¦æ¥è¿äº¤å²æ
        # å®éå®ç°ä¸­éè¦æ ¹æ®åç§å·ä½äº¤å²è§åå¤æ?        alerts = []
        for symbol in self._symbol_pnl.keys():
            # åè®¾äº¤å²æä¸ºåçº¦æä»½
            if len(symbol) >= 6:
                try:
                    contract_month = int(symbol[-4:-2])
                    contract_year = int(symbol[-6:-4]) + 2000
                    contract_date = datetime(contract_year, contract_month, 15)
                    days_to_delivery = (contract_date - now).days
                    if 0 < days_to_delivery <= int(rule.threshold):
                        if not self._can_trigger(f"{rule.name}:{symbol}", rule.cooldown_minutes):
                            continue
                        alert = RiskAlert(
                            rule_name=rule.name,
                            level=rule.level,
                            symbol=symbol,
                            message=f"åç§ {symbol} è·äº¤å²æä»?{days_to_delivery} å¤?,
                            metric_value=days_to_delivery,
                            metric_threshold=rule.threshold,
                            action_taken=rule.action,
                        )
                        await self._handle_alert(alert)
                        alerts.append(alert)
                except (ValueError, IndexError):
                    continue

        return alerts[0] if alerts else None

    async def _check_consecutive_loss(self, candidate_id: str, count: int) -> Optional[RiskAlert]:
        """æ£æ¥è¿ç»­äºæã?""
        rule = self.rules.get("consecutive_loss")
        if not rule or not rule.enabled:
            return None

        if count < rule.threshold:
            return None

        if not self._can_trigger(f"{rule.name}:{candidate_id}", rule.cooldown_minutes):
            return None

        self._paused_candidates.add(candidate_id)
        alert = RiskAlert(
            rule_name=rule.name,
            level=rule.level,
            symbol=None,
            message=f"åé?{candidate_id} è¿ç»­äºæ {count} ç¬è¶è¿éå?{int(rule.threshold)}",
            metric_value=float(count),
            metric_threshold=rule.threshold,
            action_taken=rule.action,
        )
        await self._handle_alert(alert)
        return alert

    def _can_trigger(self, key: str, cooldown_minutes: int) -> bool:
        """æ£æ¥æ¯å¦å¨å·å´æåã?""
        last = self._last_triggered.get(key)
        if last is None:
            return True
        return (datetime.utcnow() - last).total_seconds() / 60 >= cooldown_minutes

    async def _handle_alert(self, alert: RiskAlert) -> None:
        """å¤çé£æ§åè­¦ã?""
        self._alert_history.append(alert)
        self._last_triggered[alert.rule_name] = datetime.utcnow()
        if alert.symbol:
            self._last_triggered[f"{alert.rule_name}:{alert.symbol}"] = datetime.utcnow()

        logger.warning(
            f"[é£æ§åè­¦] {alert.level.value} | {alert.rule_name} | {alert.message} | å¨ä½={alert.action_taken}"
        )

        await self._publish_alert(alert)

        # æ ¹æ®å¨ä½æ§è¡ç¸åºæä½
        if alert.action_taken == "circuit_breaker":
            self._circuit_breaker_active = True
        elif alert.action_taken == "pause" and alert.symbol:
            self._paused_symbols.add(alert.symbol)

    async def _publish_alert(self, alert: RiskAlert) -> None:
        """åå¸é£æ§åè­¦å°Redisã?""
        if self.redis is None:
            return
        try:
            await self.redis.publish("risk:alerts", json.dumps(alert.to_dict(), ensure_ascii=False))
        except Exception as e:
            logger.warning(f"é£æ§åè­¦åå¸å¤±è´¥: {e}")

    # -----------------------------------------------------------------------
    # ç¶ææ´æ°æ¥å?    # -----------------------------------------------------------------------

    def update_symbol_drawdown(self, symbol: str, drawdown: float) -> None:
        """æ´æ°åç§åæ¤ã?""
        self._symbol_drawdowns[symbol] = drawdown

    def update_symbol_pnl(self, symbol: str, pnl: Decimal) -> None:
        """æ´æ°åç§çäºã?""
        self._symbol_pnl[symbol] = pnl

    def update_daily_pnl(self, pnl: Decimal) -> None:
        """æ´æ°å½æ¥çäºã?""
        today = datetime.utcnow().date()
        if today != self._daily_pnl_date:
            self._daily_pnl = Decimal("0")
            self._daily_pnl_date = today
        self._daily_pnl += pnl

    def update_margin(self, used: Decimal, total: Decimal) -> None:
        """æ´æ°ä¿è¯éã?""
        self._margin_used = used
        self._margin_total = total

    def record_trade_result(self, candidate_id: str, pnl: Decimal) -> None:
        """è®°å½äº¤æç»æï¼æ´æ°è¿ç»­äºæè®¡æ°ã?""
        if pnl < 0:
            self._consecutive_losses[candidate_id] = self._consecutive_losses.get(candidate_id, 0) + 1
        else:
            self._consecutive_losses[candidate_id] = 0

    def reset_consecutive_loss(self, candidate_id: str) -> None:
        """éç½®è¿ç»­äºæè®¡æ°ã?""
        self._consecutive_losses[candidate_id] = 0

    # -----------------------------------------------------------------------
    # æ¥è¯¢æ¥å£
    # -----------------------------------------------------------------------

    @property
    def is_circuit_breaker_active(self) -> bool:
        return self._circuit_breaker_active

    def is_symbol_paused(self, symbol: str) -> bool:
        return symbol in self._paused_symbols

    def is_candidate_paused(self, candidate_id: str) -> bool:
        return candidate_id in self._paused_candidates

    def get_paused_symbols(self) -> Set[str]:
        return set(self._paused_symbols)

    def get_paused_candidates(self) -> Set[str]:
        return set(self._paused_candidates)

    def clear_symbol_pause(self, symbol: str) -> None:
        self._paused_symbols.discard(symbol)

    def clear_candidate_pause(self, candidate_id: str) -> None:
        self._paused_candidates.discard(candidate_id)

    def reset_circuit_breaker(self) -> None:
        self._circuit_breaker_active = False
        logger.info("å¨ç³»ç»çæ­å·²æå¨éç½®")

    def get_alert_history(self, limit: int = 100) -> List[RiskAlert]:
        return self._alert_history[-limit:]

    def get_rule_config(self, name: str) -> Optional[RiskRuleConfig]:
        return self.rules.get(name)

    def update_rule_config(self, config: RiskRuleConfig) -> None:
        self.rules[config.name] = config

    def to_risk_event_model(self, alert: RiskAlert) -> RiskEvent:
        """è½¬æ¢ä¸ºORMæ¨¡åã?""
        return RiskEvent(
            event_type=alert.rule_name,
            symbol=alert.symbol,
            level=alert.level,
            message=alert.message,
            metric_value=alert.metric_value,
            metric_threshold=alert.metric_threshold,
            triggered_at=alert.timestamp,
            action_taken=alert.action_taken,
        )
