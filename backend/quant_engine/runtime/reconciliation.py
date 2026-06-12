"""
仓位对账 — 系统持仓 vs 天勤持仓实时比对

核心能力：
- 每秒比对系统持仓 vs 天勤持仓
- 不一致立即告警
- 差异类型识别（漏单、多仓、方向错误）
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Set, Tuple

from runtime.execution_gateway import ExecutionGateway, PositionSnapshot
from strategy.position_lifecycle import PositionLifecycleManager, PositionRecord

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 对账差异
# ---------------------------------------------------------------------------

class ReconcileDiffType(Enum):
    MISSING_IN_SYSTEM = "MISSING_IN_SYSTEM"      # 天勤有，系统没有
    MISSING_IN_BROKER = "MISSING_IN_BROKER"      # 系统有，天勤没有
    DIRECTION_MISMATCH = "DIRECTION_MISMATCH"    # 方向不一致
    VOLUME_MISMATCH = "VOLUME_MISMATCH"          # 手数不一致
    PRICE_MISMATCH = "PRICE_MISMATCH"            # 均价差异过大


@dataclass
class ReconcileDiff:
    """对账差异记录"""

    symbol: str
    diff_type: ReconcileDiffType
    system_value: Any
    broker_value: Any
    message: str
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "diff_type": self.diff_type.value,
            "system_value": self.system_value,
            "broker_value": self.broker_value,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class ReconcileReport:
    """对账报告"""

    timestamp: datetime
    total_symbols: int
    matched_symbols: int
    diff_count: int
    diffs: List[ReconcileDiff] = field(default_factory=list)
    system_positions: List[Dict[str, Any]] = field(default_factory=list)
    broker_positions: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "total_symbols": self.total_symbols,
            "matched_symbols": self.matched_symbols,
            "diff_count": self.diff_count,
            "diffs": [d.to_dict() for d in self.diffs],
            "system_positions": self.system_positions,
            "broker_positions": self.broker_positions,
        }


# ---------------------------------------------------------------------------
# 对账引擎
# ---------------------------------------------------------------------------

class ReconciliationEngine:
    """
    仓位对账引擎

    每秒比对系统持仓与天勤实际持仓，发现不一致立即告警。
    """

    PRICE_TOLERANCE: Decimal = Decimal("0.02")  # 均价差异容忍度 2%

    def __init__(
        self,
        gateway: ExecutionGateway,
        position_manager: PositionLifecycleManager,
        redis_client: Optional[Any] = None,
    ) -> None:
        self.gateway = gateway
        self.pm = position_manager
        self.redis = redis_client
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._last_report: Optional[ReconcileReport] = None
        self._diff_history: List[ReconcileDiff] = []
        self._alert_cooldown: Dict[str, datetime] = {}
        self._alert_interval_seconds: int = 60

    async def start(self, interval_seconds: float = 1.0) -> None:
        """启动对账循环。"""
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._reconcile_loop(interval_seconds))
        logger.info(f"对账引擎已启动，间隔={interval_seconds}s")

    async def stop(self) -> None:
        """停止对账循环。"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("对账引擎已停止")

    async def _reconcile_loop(self, interval: float) -> None:
        """对账主循环。"""
        while self._running:
            try:
                await self.run_once()
            except Exception as e:
                logger.exception(f"对账异常: {e}")
            await asyncio.sleep(interval)

    async def run_once(self) -> ReconcileReport:
        """执行一次对账。"""
        broker_positions = await self.gateway.get_positions()
        system_positions = self.pm.get_all_open_positions()

        report = self._compare(system_positions, broker_positions)
        self._last_report = report

        if report.diff_count > 0:
            self._diff_history.extend(report.diffs)
            await self._handle_diffs(report.diffs)

        return report

    def _compare(
        self,
        system_positions: List[PositionRecord],
        broker_positions: List[PositionSnapshot],
    ) -> ReconcileReport:
        """比对系统持仓与券商持仓。"""
        diffs: List[ReconcileDiff] = []

        sys_map: Dict[str, PositionRecord] = {}
        for p in system_positions:
            key = f"{p.symbol}:{p.side.value}"
            sys_map[key] = p

        broker_map: Dict[str, PositionSnapshot] = {}
        for p in broker_positions:
            dir_key = "BUY" if p.direction == "LONG" else "SELL"
            key = f"{p.symbol}:{dir_key}"
            broker_map[key] = p

        all_keys: Set[str] = set(sys_map.keys()) | set(broker_map.keys())
        matched = 0

        for key in all_keys:
            sys_pos = sys_map.get(key)
            broker_pos = broker_map.get(key)

            if sys_pos is None and broker_pos is not None:
                diffs.append(ReconcileDiff(
                    symbol=broker_pos.symbol,
                    diff_type=ReconcileDiffType.MISSING_IN_SYSTEM,
                    system_value=None,
                    broker_value=broker_pos.to_dict(),
                    message=f"天勤持仓未在系统记录: {broker_pos.symbol} {broker_pos.direction} {broker_pos.volume}手",
                ))
            elif sys_pos is not None and broker_pos is None:
                diffs.append(ReconcileDiff(
                    symbol=sys_pos.symbol,
                    diff_type=ReconcileDiffType.MISSING_IN_BROKER,
                    system_value=sys_pos.to_dict(),
                    broker_value=None,
                    message=f"系统持仓未在天勤找到: {sys_pos.symbol} {sys_pos.side.value} {sys_pos.lots}手",
                ))
            else:
                matched += 1
                # 手数比对
                if sys_pos.lots != broker_pos.volume:
                    diffs.append(ReconcileDiff(
                        symbol=sys_pos.symbol,
                        diff_type=ReconcileDiffType.VOLUME_MISMATCH,
                        system_value=sys_pos.lots,
                        broker_value=broker_pos.volume,
                        message=f"手数不一致: 系统={sys_pos.lots} 天勤={broker_pos.volume}",
                    ))

                # 均价比对
                if broker_pos.open_price > 0:
                    price_diff_pct = abs(sys_pos.entry_price - broker_pos.open_price) / broker_pos.open_price
                    if price_diff_pct > self.PRICE_TOLERANCE:
                        diffs.append(ReconcileDiff(
                            symbol=sys_pos.symbol,
                            diff_type=ReconcileDiffType.PRICE_MISMATCH,
                            system_value=float(sys_pos.entry_price),
                            broker_value=float(broker_pos.open_price),
                            message=f"均价差异过大: 系统={sys_pos.entry_price} 天勤={broker_pos.open_price} (差异{price_diff_pct:.1%})",
                        ))

        return ReconcileReport(
            timestamp=datetime.utcnow(),
            total_symbols=len(all_keys),
            matched_symbols=matched,
            diff_count=len(diffs),
            diffs=diffs,
            system_positions=[p.to_dict() for p in system_positions],
            broker_positions=[p.to_dict() for p in broker_positions],
        )

    async def _handle_diffs(self, diffs: List[ReconcileDiff]) -> None:
        """处理对账差异。"""
        now = datetime.utcnow()
        for diff in diffs:
            key = f"{diff.symbol}:{diff.diff_type.value}"
            last_alert = self._alert_cooldown.get(key)
            if last_alert and (now - last_alert).total_seconds() < self._alert_interval_seconds:
                continue

            self._alert_cooldown[key] = now
            logger.warning(f"[对账差异] {diff.message}")
            await self._publish_alert(diff)

    async def _publish_alert(self, diff: ReconcileDiff) -> None:
        """发布对账告警到Redis。"""
        if self.redis is None:
            return
        try:
            event = {
                "type": "reconcile_alert",
                "diff": diff.to_dict(),
            }
            await self.redis.publish("risk:alerts", json.dumps(event, ensure_ascii=False))
        except Exception as e:
            logger.warning(f"对账告警发布失败: {e}")

    def get_last_report(self) -> Optional[ReconcileReport]:
        """获取最后一次对账报告。"""
        return self._last_report

    def get_diff_history(self, limit: int = 100) -> List[ReconcileDiff]:
        """获取差异历史。"""
        return self._diff_history[-limit:]

    def clear_diff_history(self) -> None:
        """清空差异历史。"""
        self._diff_history.clear()
