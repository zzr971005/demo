"""
风险控制模块

提供止损、熔断、仓位限制等风险控制功能
"""

import logging
import threading
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

from quant_engine.runtime.position_tracker import (
    get_position_tracker,
    PositionTracker,
    Position,
)

logger = logging.getLogger("quant_engine.risk_manager")


class RiskLevel(Enum):
    """风险等级"""
    NORMAL = "normal"       # 正常
    WARNING = "warning"     # 警告
    DANGER = "danger"       # 危险
    CRITICAL = "critical"   # 严重


class RiskEventType(Enum):
    """风险事件类型"""
    STOP_LOSS = "stop_loss"           # 止损触发
    MAX_DRAWDOWN = "max_drawdown"     # 最大回撤超限
    DAILY_LOSS = "daily_loss"         # 日亏损超限
    POSITION_LIMIT = "position_limit" # 仓位限制
    MARGIN_CALL = "margin_call"       # 保证金不足
    PRICE_LIMIT = "price_limit"       # 价格限制
    VOLATILITY = "volatility"         # 波动率异常
    CIRCUIT_BREAKER = "circuit_breaker"  # 熔断


@dataclass
class RiskEvent:
    """风险事件"""
    event_id: str
    event_type: RiskEventType
    level: RiskLevel
    symbol: Optional[str]
    message: str
    timestamp: datetime
    
    # 触发值
    trigger_value: float
    threshold_value: float
    
    # 建议操作
    suggested_action: str
    
    # 是否已处理
    is_handled: bool = False
    handled_at: Optional[datetime] = None
    handled_by: Optional[str] = None


@dataclass
class RiskConfig:
    """风险配置"""
    # 止损配置
    stop_loss_pct: float = 0.02           # 2%止损
    trailing_stop_pct: float = 0.015      # 1.5%追踪止损
    
    # 回撤控制
    max_drawdown_pct: float = 0.10        # 10%最大回撤
    daily_loss_limit_pct: float = 0.05    # 5%日亏损限制
    
    # 仓位限制
    max_position_value: float = 100000    # 最大仓位价值
    max_margin_usage_pct: float = 0.80    # 最大保证金使用率
    max_single_position_pct: float = 0.30 # 单品种最大仓位比例
    
    # 价格限制
    max_price_deviation_pct: float = 0.02  # 最大价格偏离
    
    # 熔断配置
    circuit_breaker_levels: Dict[str, float] = field(default_factory=lambda: {
        "level1": 0.03,   # 3% 警告
        "level2": 0.05,   # 5% 减仓
        "level3": 0.08,   # 8% 停止开仓
        "level4": 0.10,   # 10% 全部平仓
    })
    
    # 波动率限制
    max_volatility_pct: float = 0.05      # 最大波动率


class RiskManager:
    """风险管理器"""
    
    def __init__(
        self,
        position_tracker: Optional[PositionTracker] = None,
        config: Optional[RiskConfig] = None,
    ):
        self.position_tracker = position_tracker or get_position_tracker()
        self.config = config or RiskConfig()
        
        self._risk_events: Dict[str, RiskEvent] = {}
        self._lock = threading.RLock()
        self._callbacks: List[Callable[[RiskEvent], None]] = []
        
        # 运行状态
        self._running = False
        self._check_interval = 5  # 检查间隔（秒）
        
        # 日盈亏跟踪
        self._daily_pnl: float = 0.0
        self._daily_start_equity: float = 0.0
        self._last_reset_date: datetime = datetime.now().date()
        
        # 历史最高权益
        self._peak_equity: float = 0.0
        
        # 熔断状态
        self._circuit_breaker_level: int = 0
        self._circuit_breaker_triggered_at: Optional[datetime] = None
    
    def start(self) -> None:
        """启动风险管理"""
        if self._running:
            return
        
        self._running = True
        import threading
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        logger.info("Risk manager started")
    
    def stop(self) -> None:
        """停止风险管理"""
        self._running = False
        if hasattr(self, '_thread'):
            self._thread.join(timeout=5)
        logger.info("Risk manager stopped")
    
    def _run(self) -> None:
        """主循环"""
        import time
        
        while self._running:
            try:
                self._check_all_risks()
                time.sleep(self._check_interval)
            except Exception as e:
                logger.error(f"Error in risk check loop: {e}")
                time.sleep(1)
    
    def _check_all_risks(self) -> None:
        """检查所有风险"""
        # 重置日盈亏（如果跨天）
        self._reset_daily_if_needed()
        
        # 检查各品种仓位风险
        positions = self.position_tracker.get_non_flat_positions()
        for position in positions:
            self._check_position_risk(position)
        
        # 检查整体账户风险
        self._check_account_risk()
    
    def _reset_daily_if_needed(self) -> None:
        """如果需要，重置日盈亏"""
        current_date = datetime.now().date()
        if current_date != self._last_reset_date:
            self._daily_pnl = 0.0
            self._last_reset_date = current_date
            self._circuit_breaker_level = 0
            logger.info("Daily risk metrics reset")
    
    def _check_position_risk(self, position: Position) -> None:
        """检查单个仓位风险"""
        # 检查止损
        self._check_stop_loss(position)
        
        # 检查仓位限制
        self._check_position_limit(position)
    
    def _check_stop_loss(self, position: Position) -> None:
        """检查止损"""
        if position.is_flat:
            return
        
        # 计算当前亏损比例
        if position.avg_price == 0:
            return
        
        if position.is_long:
            loss_pct = (position.avg_price - position.avg_price) / position.avg_price
        else:
            loss_pct = (position.avg_price - position.avg_price) / position.avg_price
        
        # 这里应该使用最新价格，简化处理使用avg_price
        # 实际需要接入行情服务获取最新价
        
        if loss_pct >= self.config.stop_loss_pct:
            self._trigger_risk_event(
                RiskEventType.STOP_LOSS,
                RiskLevel.CRITICAL,
                position.symbol,
                f"Stop loss triggered for {position.symbol}: loss {loss_pct:.2%}",
                loss_pct,
                self.config.stop_loss_pct,
                f"Close position {position.symbol}",
            )
    
    def _check_position_limit(self, position: Position) -> None:
        """检查仓位限制"""
        if position.is_flat:
            return
        
        position_value = position.market_value
        
        if position_value > self.config.max_position_value:
            self._trigger_risk_event(
                RiskEventType.POSITION_LIMIT,
                RiskLevel.WARNING,
                position.symbol,
                f"Position value {position_value:.2f} exceeds limit {self.config.max_position_value}",
                position_value,
                self.config.max_position_value,
                f"Reduce position {position.symbol}",
            )
    
    def _check_account_risk(self) -> None:
        """检查账户整体风险"""
        summary = self.position_tracker.get_position_summary()
        
        # 检查总亏损
        total_pnl = summary.get("total_pnl", 0)
        
        # 检查日亏损
        if self._daily_start_equity > 0:
            daily_loss_pct = -self._daily_pnl / self._daily_start_equity
            if daily_loss_pct >= self.config.daily_loss_limit_pct:
                self._trigger_risk_event(
                    RiskEventType.DAILY_LOSS,
                    RiskLevel.DANGER,
                    None,
                    f"Daily loss {daily_loss_pct:.2%} exceeds limit {self.config.daily_loss_limit_pct:.2%}",
                    daily_loss_pct,
                    self.config.daily_loss_limit_pct,
                    "Stop all new orders",
                )
        
        # 检查回撤
        current_equity = self._daily_start_equity + total_pnl
        if current_equity > self._peak_equity:
            self._peak_equity = current_equity
        
        if self._peak_equity > 0:
            drawdown_pct = (self._peak_equity - current_equity) / self._peak_equity
            
            if drawdown_pct >= self.config.max_drawdown_pct:
                self._trigger_risk_event(
                    RiskEventType.MAX_DRAWDOWN,
                    RiskLevel.CRITICAL,
                    None,
                    f"Max drawdown {drawdown_pct:.2%} exceeds limit {self.config.max_drawdown_pct:.2%}",
                    drawdown_pct,
                    self.config.max_drawdown_pct,
                    "Close all positions",
                )
            
            # 检查熔断
            self._check_circuit_breaker(drawdown_pct)
    
    def _check_circuit_breaker(self, drawdown_pct: float) -> None:
        """检查熔断"""
        levels = self.config.circuit_breaker_levels
        
        new_level = 0
        if drawdown_pct >= levels.get("level4", 0.10):
            new_level = 4
        elif drawdown_pct >= levels.get("level3", 0.08):
            new_level = 3
        elif drawdown_pct >= levels.get("level2", 0.05):
            new_level = 2
        elif drawdown_pct >= levels.get("level1", 0.03):
            new_level = 1
        
        if new_level > self._circuit_breaker_level:
            self._circuit_breaker_level = new_level
            self._circuit_breaker_triggered_at = datetime.now()
            
            actions = {
                1: "Warning: Monitor closely",
                2: "Reduce positions by 30%",
                3: "Stop new orders",
                4: "Emergency close all positions",
            }
            
            self._trigger_risk_event(
                RiskEventType.CIRCUIT_BREAKER,
                RiskLevel.CRITICAL if new_level >= 3 else RiskLevel.DANGER,
                None,
                f"Circuit breaker level {new_level} triggered",
                drawdown_pct,
                levels.get(f"level{new_level}", 0),
                actions.get(new_level, "Unknown action"),
            )
    
    def _trigger_risk_event(
        self,
        event_type: RiskEventType,
        level: RiskLevel,
        symbol: Optional[str],
        message: str,
        trigger_value: float,
        threshold_value: float,
        suggested_action: str,
    ) -> RiskEvent:
        """触发风险事件"""
        event_id = f"RISK{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        event = RiskEvent(
            event_id=event_id,
            event_type=event_type,
            level=level,
            symbol=symbol,
            message=message,
            timestamp=datetime.now(),
            trigger_value=trigger_value,
            threshold_value=threshold_value,
            suggested_action=suggested_action,
        )
        
        with self._lock:
            self._risk_events[event_id] = event
        
        logger.warning(f"Risk event triggered: {message}")
        
        # 通知回调
        self._notify_callbacks(event)
        
        return event
    
    def handle_risk_event(self, event_id: str, handled_by: str) -> bool:
        """处理风险事件"""
        with self._lock:
            event = self._risk_events.get(event_id)
            if not event:
                return False
            
            event.is_handled = True
            event.handled_at = datetime.now()
            event.handled_by = handled_by
            
            logger.info(f"Risk event {event_id} handled by {handled_by}")
            return True
    
    def get_risk_events(
        self,
        event_type: Optional[RiskEventType] = None,
        level: Optional[RiskLevel] = None,
        symbol: Optional[str] = None,
        unhandled_only: bool = False,
        limit: int = 100,
    ) -> List[RiskEvent]:
        """获取风险事件列表"""
        with self._lock:
            events = list(self._risk_events.values())
            
            if event_type:
                events = [e for e in events if e.event_type == event_type]
            
            if level:
                events = [e for e in events if e.level == level]
            
            if symbol:
                events = [e for e in events if e.symbol == symbol]
            
            if unhandled_only:
                events = [e for e in events if not e.is_handled]
            
            # 按时间倒序
            events.sort(key=lambda x: x.timestamp, reverse=True)
            
            return events[:limit]
    
    def get_risk_summary(self) -> Dict[str, Any]:
        """获取风险汇总"""
        with self._lock:
            unhandled_events = [e for e in self._risk_events.values() if not e.is_handled]
            
            return {
                "circuit_breaker_level": self._circuit_breaker_level,
                "daily_pnl": self._daily_pnl,
                "peak_equity": self._peak_equity,
                "total_risk_events": len(self._risk_events),
                "unhandled_events": len(unhandled_events),
                "critical_events": len([e for e in unhandled_events if e.level == RiskLevel.CRITICAL]),
            }
    
    def add_callback(self, callback: Callable[[RiskEvent], None]) -> None:
        """添加风险事件回调"""
        self._callbacks.append(callback)
    
    def remove_callback(self, callback: Callable[[RiskEvent], None]) -> None:
        """移除风险事件回调"""
        if callback in self._callbacks:
            self._callbacks.remove(callback)
    
    def _notify_callbacks(self, event: RiskEvent) -> None:
        """通知回调"""
        for callback in self._callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Error in risk callback: {e}")
    
    def reset_circuit_breaker(self) -> None:
        """重置熔断"""
        self._circuit_breaker_level = 0
        self._circuit_breaker_triggered_at = None
        logger.info("Circuit breaker reset")


# 全局风险管理器实例
_risk_manager: Optional[RiskManager] = None


def get_risk_manager(
    position_tracker: Optional[PositionTracker] = None,
    config: Optional[RiskConfig] = None,
) -> RiskManager:
    """获取全局风险管理器实例"""
    global _risk_manager
    
    if _risk_manager is None:
        _risk_manager = RiskManager(position_tracker, config)
    
    return _risk_manager


def reset_risk_manager() -> None:
    """重置全局风险管理器实例"""
    global _risk_manager
    if _risk_manager:
        _risk_manager.stop()
    _risk_manager = None
