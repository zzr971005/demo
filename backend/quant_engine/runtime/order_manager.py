"""
订单管理模块

提供订单创建、跟踪、取消等功能
"""

import logging
import threading
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from decimal import Decimal

logger = logging.getLogger("quant_engine.order_manager")


class OrderStatus(Enum):
    """订单状态"""
    PENDING = "pending"           # 待提交
    SUBMITTED = "submitted"       # 已提交
    PARTIAL_FILLED = "partial_filled"  # 部分成交
    FILLED = "filled"             # 全部成交
    CANCELLED = "cancelled"       # 已取消
    REJECTED = "rejected"         # 已拒绝
    EXPIRED = "expired"           # 已过期


class OrderDirection(Enum):
    """订单方向"""
    BUY = "buy"
    SELL = "sell"


class OrderOffset(Enum):
    """开平方向"""
    OPEN = "open"                 # 开仓
    CLOSE = "close"               # 平仓
    CLOSE_TODAY = "close_today"   # 平今（IF禁止）


class OrderType(Enum):
    """订单类型"""
    MARKET = "market"             # 市价单
    LIMIT = "limit"               # 限价单
    STOP = "stop"                 # 止损单
    STOP_LIMIT = "stop_limit"     # 止损限价单


@dataclass
class Order:
    """订单对象"""
    order_id: str
    symbol: str
    direction: OrderDirection
    offset: OrderOffset
    volume: int
    price: Optional[float] = None
    order_type: OrderType = OrderType.LIMIT
    status: OrderStatus = OrderStatus.PENDING
    
    # 时间戳
    created_at: datetime = field(default_factory=datetime.now)
    submitted_at: Optional[datetime] = None
    filled_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    
    # 成交信息
    filled_volume: int = 0
    filled_price: float = 0.0
    filled_amount: float = 0.0
    
    # 其他信息
    strategy_id: Optional[str] = None
    factor_id: Optional[str] = None
    comment: Optional[str] = None
    
    # 错误信息
    error_message: Optional[str] = None
    
    @property
    def remaining_volume(self) -> int:
        """剩余未成交数量"""
        return self.volume - self.filled_volume
    
    @property
    def is_active(self) -> bool:
        """订单是否活跃"""
        return self.status in [
            OrderStatus.PENDING,
            OrderStatus.SUBMITTED,
            OrderStatus.PARTIAL_FILLED,
        ]
    
    @property
    def is_completed(self) -> bool:
        """订单是否已完成"""
        return self.status in [
            OrderStatus.FILLED,
            OrderStatus.CANCELLED,
            OrderStatus.REJECTED,
            OrderStatus.EXPIRED,
        ]


@dataclass
class Trade:
    """成交记录"""
    trade_id: str
    order_id: str
    symbol: str
    direction: OrderDirection
    offset: OrderOffset
    volume: int
    price: float
    amount: float
    timestamp: datetime
    commission: float = 0.0
    
    # 关联信息
    strategy_id: Optional[str] = None
    factor_id: Optional[str] = None


class OrderManager:
    """订单管理器"""
    
    def __init__(self):
        self._orders: Dict[str, Order] = {}
        self._trades: Dict[str, Trade] = {}
        self._order_trades: Dict[str, List[str]] = {}  # order_id -> trade_ids
        
        self._lock = threading.RLock()
        self._callbacks: List[Callable[[Order], None]] = []
        
        # 订单ID生成器
        self._order_counter = 0
        self._trade_counter = 0
    
    def _generate_order_id(self) -> str:
        """生成订单ID"""
        with self._lock:
            self._order_counter += 1
            return f"ORD{datetime.now().strftime('%Y%m%d%H%M%S')}{self._order_counter:06d}"
    
    def _generate_trade_id(self) -> str:
        """生成成交ID"""
        with self._lock:
            self._trade_counter += 1
            return f"TRD{datetime.now().strftime('%Y%m%d%H%M%S')}{self._trade_counter:06d}"
    
    def create_order(
        self,
        symbol: str,
        direction: OrderDirection,
        offset: OrderOffset,
        volume: int,
        price: Optional[float] = None,
        order_type: OrderType = OrderType.LIMIT,
        strategy_id: Optional[str] = None,
        factor_id: Optional[str] = None,
        comment: Optional[str] = None,
    ) -> Order:
        """创建订单"""
        with self._lock:
            order_id = self._generate_order_id()
            
            order = Order(
                order_id=order_id,
                symbol=symbol,
                direction=direction,
                offset=offset,
                volume=volume,
                price=price,
                order_type=order_type,
                strategy_id=strategy_id,
                factor_id=factor_id,
                comment=comment,
            )
            
            self._orders[order_id] = order
            self._order_trades[order_id] = []
            
            logger.info(f"Created order: {order_id} {symbol} {direction.value} {volume}@{price}")
            
            return order
    
    def submit_order(self, order_id: str) -> bool:
        """提交订单"""
        with self._lock:
            order = self._orders.get(order_id)
            if not order:
                logger.error(f"Order not found: {order_id}")
                return False
            
            if order.status != OrderStatus.PENDING:
                logger.error(f"Order {order_id} is not pending")
                return False
            
            order.status = OrderStatus.SUBMITTED
            order.submitted_at = datetime.now()
            
            logger.info(f"Submitted order: {order_id}")
            
            self._notify_callbacks(order)
            return True
    
    def fill_order(
        self,
        order_id: str,
        volume: int,
        price: float,
        commission: float = 0.0,
    ) -> Optional[Trade]:
        """成交订单"""
        with self._lock:
            order = self._orders.get(order_id)
            if not order:
                logger.error(f"Order not found: {order_id}")
                return None
            
            if not order.is_active:
                logger.error(f"Order {order_id} is not active")
                return None
            
            # 创建成交记录
            trade_id = self._generate_trade_id()
            trade = Trade(
                trade_id=trade_id,
                order_id=order_id,
                symbol=order.symbol,
                direction=order.direction,
                offset=order.offset,
                volume=volume,
                price=price,
                amount=volume * price,
                timestamp=datetime.now(),
                commission=commission,
                strategy_id=order.strategy_id,
                factor_id=order.factor_id,
            )
            
            self._trades[trade_id] = trade
            self._order_trades[order_id].append(trade_id)
            
            # 更新订单状态
            order.filled_volume += volume
            order.filled_amount += volume * price
            
            if order.filled_volume >= order.volume:
                order.status = OrderStatus.FILLED
                order.filled_at = datetime.now()
                order.filled_price = order.filled_amount / order.filled_volume
            else:
                order.status = OrderStatus.PARTIAL_FILLED
            
            logger.info(f"Filled order: {order_id} {volume}@{price}")
            
            self._notify_callbacks(order)
            return trade
    
    def cancel_order(self, order_id: str, reason: Optional[str] = None) -> bool:
        """取消订单"""
        with self._lock:
            order = self._orders.get(order_id)
            if not order:
                logger.error(f"Order not found: {order_id}")
                return False
            
            if not order.is_active:
                logger.error(f"Order {order_id} is not active")
                return False
            
            order.status = OrderStatus.CANCELLED
            order.cancelled_at = datetime.now()
            order.comment = reason or order.comment
            
            logger.info(f"Cancelled order: {order_id} reason={reason}")
            
            self._notify_callbacks(order)
            return True
    
    def reject_order(self, order_id: str, reason: str) -> bool:
        """拒绝订单"""
        with self._lock:
            order = self._orders.get(order_id)
            if not order:
                logger.error(f"Order not found: {order_id}")
                return False
            
            order.status = OrderStatus.REJECTED
            order.error_message = reason
            
            logger.warning(f"Rejected order: {order_id} reason={reason}")
            
            self._notify_callbacks(order)
            return True
    
    def expire_order(self, order_id: str) -> bool:
        """订单过期"""
        with self._lock:
            order = self._orders.get(order_id)
            if not order:
                logger.error(f"Order not found: {order_id}")
                return False
            
            if not order.is_active:
                return False
            
            order.status = OrderStatus.EXPIRED
            
            logger.info(f"Expired order: {order_id}")
            
            self._notify_callbacks(order)
            return True
    
    def get_order(self, order_id: str) -> Optional[Order]:
        """获取订单"""
        with self._lock:
            return self._orders.get(order_id)
    
    def get_orders(
        self,
        symbol: Optional[str] = None,
        status: Optional[OrderStatus] = None,
        strategy_id: Optional[str] = None,
    ) -> List[Order]:
        """获取订单列表"""
        with self._lock:
            orders = list(self._orders.values())
            
            if symbol:
                orders = [o for o in orders if o.symbol == symbol]
            
            if status:
                orders = [o for o in orders if o.status == status]
            
            if strategy_id:
                orders = [o for o in orders if o.strategy_id == strategy_id]
            
            return orders
    
    def get_active_orders(
        self,
        symbol: Optional[str] = None,
        strategy_id: Optional[str] = None,
    ) -> List[Order]:
        """获取活跃订单"""
        with self._lock:
            orders = list(self._orders.values())
            orders = [o for o in orders if o.is_active]
            
            if symbol:
                orders = [o for o in orders if o.symbol == symbol]
            
            if strategy_id:
                orders = [o for o in orders if o.strategy_id == strategy_id]
            
            return orders
    
    def get_trade(self, trade_id: str) -> Optional[Trade]:
        """获取成交记录"""
        with self._lock:
            return self._trades.get(trade_id)
    
    def get_trades(
        self,
        order_id: Optional[str] = None,
        symbol: Optional[str] = None,
        strategy_id: Optional[str] = None,
    ) -> List[Trade]:
        """获取成交记录列表"""
        with self._lock:
            if order_id:
                trade_ids = self._order_trades.get(order_id, [])
                return [self._trades[tid] for tid in trade_ids]
            
            trades = list(self._trades.values())
            
            if symbol:
                trades = [t for t in trades if t.symbol == symbol]
            
            if strategy_id:
                trades = [t for t in trades if t.strategy_id == strategy_id]
            
            return trades
    
    def add_callback(self, callback: Callable[[Order], None]) -> None:
        """添加订单状态变更回调"""
        self._callbacks.append(callback)
    
    def remove_callback(self, callback: Callable[[Order], None]) -> None:
        """移除订单状态变更回调"""
        if callback in self._callbacks:
            self._callbacks.remove(callback)
    
    def _notify_callbacks(self, order: Order) -> None:
        """通知回调"""
        for callback in self._callbacks:
            try:
                callback(order)
            except Exception as e:
                logger.error(f"Error in order callback: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            total_orders = len(self._orders)
            active_orders = len([o for o in self._orders.values() if o.is_active])
            filled_orders = len([o for o in self._orders.values() if o.status == OrderStatus.FILLED])
            cancelled_orders = len([o for o in self._orders.values() if o.status == OrderStatus.CANCELLED])
            rejected_orders = len([o for o in self._orders.values() if o.status == OrderStatus.REJECTED])
            
            total_trades = len(self._trades)
            total_volume = sum(t.volume for t in self._trades.values())
            total_amount = sum(t.amount for t in self._trades.values())
            total_commission = sum(t.commission for t in self._trades.values())
            
            return {
                "total_orders": total_orders,
                "active_orders": active_orders,
                "filled_orders": filled_orders,
                "cancelled_orders": cancelled_orders,
                "rejected_orders": rejected_orders,
                "total_trades": total_trades,
                "total_volume": total_volume,
                "total_amount": total_amount,
                "total_commission": total_commission,
            }
    
    def clear_completed_orders(self, max_age_hours: int = 24) -> int:
        """清理已完成的订单"""
        with self._lock:
            cutoff = datetime.now() - __import__('datetime').timedelta(hours=max_age_hours)
            
            to_remove = [
                oid for oid, order in self._orders.items()
                if order.is_completed and order.created_at < cutoff
            ]
            
            for oid in to_remove:
                del self._orders[oid]
                del self._order_trades[oid]
            
            logger.info(f"Cleared {len(to_remove)} completed orders")
            return len(to_remove)


# 全局订单管理器实例
_order_manager: Optional[OrderManager] = None


def get_order_manager() -> OrderManager:
    """获取全局订单管理器实例"""
    global _order_manager
    
    if _order_manager is None:
        _order_manager = OrderManager()
    
    return _order_manager


def reset_order_manager() -> None:
    """重置全局订单管理器实例"""
    global _order_manager
    _order_manager = None
