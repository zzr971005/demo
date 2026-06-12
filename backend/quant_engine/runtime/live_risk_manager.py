"""
实盘风控管理器 - 账户级、单品种、策略切换、紧急风控
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """风险等级"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class LiveRiskManager:
    """实盘风控管理器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化实盘风控管理器
        
        Parameters
        ----------
        config : Dict[str, Any]
            配置字典
        """
        self.config = config or {}
        
        # 账户级风控
        self.max_total_margin_ratio = self.config.get("max_total_margin_ratio", 0.4)
        self.daily_max_loss_ratio = self.config.get("daily_max_loss_ratio", 0.03)
        self.max_drawdown_ratio = self.config.get("max_drawdown_ratio", 0.08)
        
        # 单品种风控
        self.max_position_ratio = self.config.get("max_position_ratio", 0.2)
        self.max_positions_per_symbol = self.config.get("max_positions_per_symbol", 1)
        self.single_symbol_max_dd = self.config.get("single_symbol_max_dd", 0.05)
        
        # 紧急风控
        self.emergency_close_all_threshold = self.config.get("emergency_close_all_threshold", 0.05)
        self.circuit_breaker_enabled = self.config.get("circuit_breaker_enabled", True)
        self.circuit_breaker_level = self.config.get("circuit_breaker_level", 3)
        
        # 风控事件计数
        self.consecutive_errors = 0
        self.risk_events: List[Dict[str, Any]] = []
    
    def check_account_risk(
        self,
        account_balance: float,
        total_margin: float,
        daily_pnl: float,
        max_drawdown: float
    ) -> tuple[bool, Optional[Dict[str, Any]]]:
        """
        检查账户级风控
        
        Parameters
        ----------
        account_balance : float
            账户余额
        total_margin : float
            总保证金
        daily_pnl : float
            当日盈亏
        max_drawdown : float
            最大回撤
        
        Returns
        -------
        tuple[bool, Optional[Dict[str, Any]]]
            (是否通过, 风控事件)
        """
        # 检查总保证金占比
        margin_ratio = total_margin / account_balance if account_balance > 0 else 0
        if margin_ratio > self.max_total_margin_ratio:
            event = {
                "event_type": "MARGIN_EXCEEDED",
                "level": RiskLevel.HIGH.value,
                "trigger_value": margin_ratio,
                "threshold_value": self.max_total_margin_ratio,
                "message": f"总保证金占比超限: {margin_ratio:.2%} > {self.max_total_margin_ratio:.2%}",
                "action_taken": "REDUCE_POSITIONS"
            }
            self._record_risk_event(event)
            return False, event
        
        # 检查当日亏损
        daily_loss_ratio = abs(daily_pnl) / account_balance if account_balance > 0 and daily_pnl < 0 else 0
        if daily_loss_ratio > self.daily_max_loss_ratio:
            event = {
                "event_type": "DAILY_LOSS_EXCEEDED",
                "level": RiskLevel.CRITICAL.value,
                "trigger_value": daily_loss_ratio,
                "threshold_value": self.daily_max_loss_ratio,
                "message": f"当日亏损超限: {daily_loss_ratio:.2%} > {self.daily_max_loss_ratio:.2%}",
                "action_taken": "STOP_TRADING"
            }
            self._record_risk_event(event)
            return False, event
        
        # 检查最大回撤
        if max_drawdown > self.max_drawdown_ratio:
            event = {
                "event_type": "MAX_DRAWDOWN_EXCEEDED",
                "level": RiskLevel.CRITICAL.value,
                "trigger_value": max_drawdown,
                "threshold_value": self.max_drawdown_ratio,
                "message": f"最大回撤超限: {max_drawdown:.2%} > {self.max_drawdown_ratio:.2%}",
                "action_taken": "REDUCE_POSITIONS"
            }
            self._record_risk_event(event)
            return False, event
        
        return True, None
    
    def check_symbol_risk(
        self,
        symbol: str,
        position: Dict[str, Any],
        account_balance: float,
        symbol_margin: float,
        symbol_drawdown: float
    ) -> tuple[bool, Optional[Dict[str, Any]]]:
        """
        检查单品种风控
        
        Parameters
        ----------
        symbol : str
            品种代码
        position : Dict[str, Any]
            持仓信息
        account_balance : float
            账户余额
        symbol_margin : float
            品种保证金
        symbol_drawdown : float
            品种回撤
        
        Returns
        -------
        tuple[bool, Optional[Dict[str, Any]]]
            (是否通过, 风控事件)
        """
        # 检查单品种保证金占比
        margin_ratio = symbol_margin / account_balance if account_balance > 0 else 0
        if margin_ratio > self.max_position_ratio:
            event = {
                "event_type": "SYMBOL_MARGIN_EXCEEDED",
                "level": RiskLevel.HIGH.value,
                "symbol": symbol,
                "trigger_value": margin_ratio,
                "threshold_value": self.max_position_ratio,
                "message": f"品种 {symbol} 保证金占比超限: {margin_ratio:.2%} > {self.max_position_ratio:.2%}",
                "action_taken": "REDUCE_POSITION"
            }
            self._record_risk_event(event)
            return False, event
        
        # 检查单品种回撤
        if symbol_drawdown > self.single_symbol_max_dd:
            event = {
                "event_type": "SYMBOL_DRAWDOWN_EXCEEDED",
                "level": RiskLevel.HIGH.value,
                "symbol": symbol,
                "trigger_value": symbol_drawdown,
                "threshold_value": self.single_symbol_max_dd,
                "message": f"品种 {symbol} 回撤超限: {symbol_drawdown:.2%} > {self.single_symbol_max_dd:.2%}",
                "action_taken": "CLOSE_POSITION"
            }
            self._record_risk_event(event)
            return False, event
        
        return True, None
    
    def check_emergency_risk(
        self,
        account_balance: float,
        total_pnl: float
    ) -> tuple[bool, Optional[Dict[str, Any]]]:
        """
        检查紧急风控
        
        Parameters
        ----------
        account_balance : float
            账户余额
        total_pnl : float
            总盈亏
        
        Returns
        -------
        tuple[bool, Optional[Dict[str, Any]]]
            (是否通过, 风控事件)
        """
        # 检查紧急平仓阈值
        loss_ratio = abs(total_pnl) / account_balance if account_balance > 0 and total_pnl < 0 else 0
        if loss_ratio > self.emergency_close_all_threshold:
            event = {
                "event_type": "EMERGENCY_CLOSE_ALL",
                "level": RiskLevel.CRITICAL.value,
                "trigger_value": loss_ratio,
                "threshold_value": self.emergency_close_all_threshold,
                "message": f"触发紧急平仓: 亏损 {loss_ratio:.2%} > {self.emergency_close_all_threshold:.2%}",
                "action_taken": "CLOSE_ALL_POSITIONS"
            }
            self._record_risk_event(event)
            return False, event
        
        return True, None
    
    def trigger_circuit_breaker(self, error_count: int) -> bool:
        """
        触发熔断
        
        Parameters
        ----------
        error_count : int
            错误计数
        
        Returns
        -------
        bool
            是否触发熔断
        """
        if not self.circuit_breaker_enabled:
            return False
        
        if error_count >= self.circuit_breaker_level:
            event = {
                "event_type": "CIRCUIT_BREAKER",
                "level": RiskLevel.CRITICAL.value,
                "trigger_value": error_count,
                "threshold_value": self.circuit_breaker_level,
                "message": f"触发熔断: 连续错误 {error_count} >= {self.circuit_breaker_level}",
                "action_taken": "STOP_ALL_TRADING"
            }
            self._record_risk_event(event)
            return True
        
        return False
    
    def _record_risk_event(self, event: Dict[str, Any]):
        """
        记录风控事件
        
        Parameters
        ----------
        event : Dict[str, Any]
            风控事件
        """
        event["created_at"] = datetime.utcnow()
        event["is_resolved"] = False
        self.risk_events.append(event)
        logger.warning(f"风控事件: {event['message']}")
    
    def get_risk_events(
        self,
        symbol: Optional[str] = None,
        level: Optional[str] = None,
        resolved: Optional[bool] = None
    ) -> List[Dict[str, Any]]:
        """
        获取风控事件
        
        Parameters
        ----------
        symbol : Optional[str]
            品种代码
        level : Optional[str]
            风险等级
        resolved : Optional[bool]
            是否已解决
        
        Returns
        -------
        List[Dict[str, Any]]
            风控事件列表
        """
        events = self.risk_events
        
        if symbol:
            events = [e for e in events if e.get("symbol") == symbol]
        
        if level:
            events = [e for e in events if e.get("level") == level]
        
        if resolved is not None:
            events = [e for e in events if e.get("is_resolved") == resolved]
        
        return events
    
    def resolve_risk_event(self, event_index: int, handler: str, action: str):
        """
        解决风控事件
        
        Parameters
        ----------
        event_index : int
            事件索引
        handler : str
            处理人
        action : str
            采取的行动
        """
        if 0 <= event_index < len(self.risk_events):
            event = self.risk_events[event_index]
            event["is_resolved"] = True
            event["resolved_at"] = datetime.utcnow()
            event["handler"] = handler
            event["action_taken"] = action
            logger.info(f"风控事件已解决: {event['event_type']}")
    
    def get_risk_summary(self) -> Dict[str, Any]:
        """
        获取风控摘要
        
        Returns
        -------
        Dict[str, Any]
            风控摘要
        """
        total_events = len(self.risk_events)
        unresolved_events = len([e for e in self.risk_events if not e.get("is_resolved", False)])
        critical_events = len([e for e in self.risk_events if e.get("level") == RiskLevel.CRITICAL.value])
        
        return {
            "total_events": total_events,
            "unresolved_events": unresolved_events,
            "critical_events": critical_events,
            "consecutive_errors": self.consecutive_errors,
            "circuit_breaker_enabled": self.circuit_breaker_enabled,
            "circuit_breaker_level": self.circuit_breaker_level
        }
