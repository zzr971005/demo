"""
交易执行网关

整合订单管理、仓位跟踪、风险控制和TQSDK执行
提供统一的交易接口
"""

import logging
import threading
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from quant_engine.runtime.order_manager import (
    get_order_manager,
    OrderManager,
    Order,
    OrderDirection,
    OrderOffset,
    OrderType,
    OrderStatus,
)
from quant_engine.runtime.position_tracker import (
    get_position_tracker,
    PositionTracker,
)
from quant_engine.runtime.risk_manager import (
    get_risk_manager,
    RiskManager,
    RiskEvent,
    RiskConfig,
)
from quant_engine.runtime.tqsdk_executor import (
    get_tqsdk_executor,
    TqsdkExecutor,
    TqsdkConfig,
)

logger = logging.getLogger("quant_engine.execution_gateway")


class TradingMode(Enum):
    """交易模式"""
    MOCK = "mock"       # 模拟交易
    PAPER = "paper"     # 模拟账户
    LIVE = "live"       # 实盘交易


@dataclass
class TradingConfig:
    """交易配置"""
    mode: TradingMode = TradingMode.MOCK
    account_id: Optional[str] = None
    password: Optional[str] = None
    
    # 风险控制配置
    risk_config: Optional[RiskConfig] = None
    
    # 自动交易配置
    auto_submit: bool = True      # 自动提交订单
    auto_cancel_timeout: int = 30  # 自动撤单超时（秒）


class ExecutionGateway:
    """交易执行网关"""
    
    def __init__(
        self,
        order_manager: Optional[OrderManager] = None,
        position_tracker: Optional[PositionTracker] = None,
        risk_manager: Optional[RiskManager] = None,
        tqsdk_executor: Optional[TqsdkExecutor] = None,
        config: Optional[TradingConfig] = None,
    ):
        # 各模块实例
        self.order_manager = order_manager or get_order_manager()
        self.position_tracker = position_tracker or get_position_tracker()
        self.risk_manager = risk_manager or get_risk_manager()
        self.tqsdk_executor = tqsdk_executor or get_tqsdk_executor()
        self.config = config or TradingConfig()
        
        # 运行状态
        self._running = False
        self._connected = False
        
        # 回调
        self._callbacks: List[Callable[[str, Any], None]] = []
        
        # 锁
        self._lock = threading.RLock()
        
        # 注册风险事件回调
        self.risk_manager.add_callback(self._on_risk_event)
    
    def start(self) -> bool:
        """启动交易网关"""
        if self._running:
            return True
        
        logger.info(f"Starting execution gateway in {self.config.mode.value} mode...")
        
        # 连接TQSDK
        if self.config.mode in [TradingMode.PAPER, TradingMode.LIVE]:
            tq_config = TqsdkConfig(
                account_id=self.config.account_id,
                password=self.config.password,
                mock=(self.config.mode == TradingMode.PAPER),
            )
            self.tqsdk_executor.config = tq_config
            
            if not self.tqsdk_executor.connect():
                logger.error("Failed to connect to TQSDK")
                return False
        
        # 启动风险管理
        self.risk_manager.start()
        
        self._running = True
        self._connected = True
        
        logger.info("Execution gateway started")
        return True
    
    def stop(self) -> None:
        """停止交易网关"""
        if not self._running:
            return
        
        logger.info("Stopping execution gateway...")
        
        self._running = False
        self._connected = False
        
        # 停止风险管理
        self.risk_manager.stop()
        
        # 断开TQSDK
        self.tqsdk_executor.disconnect()
        
        logger.info("Execution gateway stopped")
    
    def is_running(self) -> bool:
        """检查运行状态"""
        return self._running
    
    def is_connected(self) -> bool:
        """检查连接状态"""
        return self._connected
    
    def place_order(
        self,
        symbol: str,
        direction: str,  # buy/sell
        offset: str,     # open/close/close_today
        volume: int,
        price: Optional[float] = None,
        order_type: str = "limit",
        strategy_id: Optional[str] = None,
        factor_id: Optional[str] = None,
        comment: Optional[str] = None,
    ) -> Dict[str, Any]:
        """下单"""
        try:
            # 转换枚举
            dir_enum = OrderDirection(direction.lower())
            offset_enum = OrderOffset(offset.lower())
            type_enum = OrderType(order_type.lower())
            
            # 检查熔断状态
            risk_summary = self.risk_manager.get_risk_summary()
            if risk_summary["circuit_breaker_level"] >= 3:
                return {
                    "success": False,
                    "error": "Circuit breaker level 3 or above, trading suspended",
                }
            
            # 创建订单
            order = self.order_manager.create_order(
                symbol=symbol,
                direction=dir_enum,
                offset=offset_enum,
                volume=volume,
                price=price,
                order_type=type_enum,
                strategy_id=strategy_id,
                factor_id=factor_id,
                comment=comment,
            )
            
            # 自动提交订单
            if self.config.auto_submit:
                if self.config.mode == TradingMode.MOCK:
                    # 模拟模式直接提交
                    self.tqsdk_executor._simulate_order(order.order_id)
                else:
                    # 实盘/模拟账户模式
                    self.tqsdk_executor.submit_order(order.order_id)
            
            return {
                "success": True,
                "order_id": order.order_id,
                "status": order.status.value,
                "message": "Order placed successfully",
            }
            
        except Exception as e:
            logger.error(f"Failed to place order: {e}")
            return {
                "success": False,
                "error": str(e),
            }
    
    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """撤单"""
        order = self.order_manager.get_order(order_id)
        if not order:
            return {
                "success": False,
                "error": "Order not found",
            }
        
        if not order.is_active:
            return {
                "success": False,
                "error": f"Order is not active, status: {order.status.value}",
            }
        
        # 取消TQSDK订单
        if self.config.mode != TradingMode.MOCK:
            if not self.tqsdk_executor.cancel_order(order_id):
                return {
                    "success": False,
                    "error": "Failed to cancel order in TQSDK",
                }
        
        # 更新本地订单状态
        if self.order_manager.cancel_order(order_id, "User cancelled"):
            return {
                "success": True,
                "message": "Order cancelled",
            }
        
        return {
            "success": False,
            "error": "Failed to cancel order",
        }
    
    def close_position(
        self,
        symbol: str,
        price: Optional[float] = None,
    ) -> Dict[str, Any]:
        """平仓"""
        position = self.position_tracker.get_position(symbol)
        if not position or position.is_flat:
            return {
                "success": False,
                "error": "No position to close",
            }
        
        # 确定平仓方向
        direction = "sell" if position.is_long else "buy"
        offset = "close"
        
        # 如果未指定价格，使用市价单
        order_type = "market" if price is None else "limit"
        
        return self.place_order(
            symbol=symbol,
            direction=direction,
            offset=offset,
            volume=position.volume,
            price=price,
            order_type=order_type,
            comment="Close position",
        )
    
    def close_all_positions(self) -> Dict[str, Any]:
        """平掉所有仓位"""
        positions = self.position_tracker.get_non_flat_positions()
        
        results = []
        for position in positions:
            result = self.close_position(position.symbol)
            results.append({
                "symbol": position.symbol,
                "result": result,
            })
        
        return {
            "success": True,
            "message": f"Closing {len(positions)} positions",
            "results": results,
        }
    
    def emergency_close_all(self) -> Dict[str, Any]:
        """紧急平仓（用于熔断）"""
        logger.critical("EMERGENCY CLOSE ALL POSITIONS")
        
        # 取消所有活跃订单
        active_orders = self.order_manager.get_active_orders()
        for order in active_orders:
            self.cancel_order(order.order_id)
        
        # 平掉所有仓位
        return self.close_all_positions()
    
    def get_account_info(self) -> Dict[str, Any]:
        """获取账户信息"""
        if self.config.mode == TradingMode.MOCK:
            # 模拟账户信息
            summary = self.position_tracker.get_position_summary()
            return {
                "mode": "mock",
                "connected": True,
                "balance": 1000000.0,
                "available": 1000000.0 - summary.get("total_margin", 0),
                "margin": summary.get("total_margin", 0),
                "float_profit": summary.get("total_unrealized_pnl", 0),
                "close_profit": summary.get("total_realized_pnl", 0),
            }
        else:
            # 从TQSDK获取
            return self.tqsdk_executor.get_account_info()
    
    def get_trading_status(self) -> Dict[str, Any]:
        """获取交易状态"""
        risk_summary = self.risk_manager.get_risk_summary()
        
        return {
            "running": self._running,
            "connected": self._connected,
            "mode": self.config.mode.value,
            "circuit_breaker_level": risk_summary["circuit_breaker_level"],
            "can_trade": (
                self._running and 
                self._connected and 
                risk_summary["circuit_breaker_level"] < 3
            ),
            "risk_status": "critical" if risk_summary["circuit_breaker_level"] >= 3 else (
                "warning" if risk_summary["circuit_breaker_level"] >= 1 else "normal"
            ),
        }
    
    def _on_risk_event(self, event: RiskEvent) -> None:
        """处理风险事件"""
        logger.warning(f"Risk event received: {event.message}")
        
        # 根据风险等级自动处理
        if event.level.value == "critical":
            if event.event_type.value == "circuit_breaker" and event.trigger_value >= 0.10:
                # 熔断级别4，紧急平仓
                self.emergency_close_all()
            elif event.event_type.value == "max_drawdown":
                # 最大回撤超限，减仓
                self.close_all_positions()
        
        # 通知回调
        self._notify_callbacks("risk_event", event)
    
    def add_callback(self, callback: Callable[[str, Any], None]) -> None:
        """添加回调"""
        self._callbacks.append(callback)
    
    def remove_callback(self, callback: Callable[[str, Any], None]) -> None:
        """移除回调"""
        if callback in self._callbacks:
            self._callbacks.remove(callback)
    
    def _notify_callbacks(self, event_type: str, data: Any) -> None:
        """通知回调"""
        for callback in self._callbacks:
            try:
                callback(event_type, data)
            except Exception as e:
                logger.error(f"Error in callback: {e}")


# 全局网关实例
_gateway: Optional[ExecutionGateway] = None


def get_execution_gateway(
    order_manager: Optional[OrderManager] = None,
    position_tracker: Optional[PositionTracker] = None,
    risk_manager: Optional[RiskManager] = None,
    tqsdk_executor: Optional[TqsdkExecutor] = None,
    config: Optional[TradingConfig] = None,
) -> ExecutionGateway:
    """获取全局网关实例"""
    global _gateway
    
    if _gateway is None:
        _gateway = ExecutionGateway(
            order_manager,
            position_tracker,
            risk_manager,
            tqsdk_executor,
            config,
        )
    
    return _gateway


def reset_execution_gateway() -> None:
    """重置全局网关实例"""
    global _gateway
    if _gateway:
        _gateway.stop()
    _gateway = None
