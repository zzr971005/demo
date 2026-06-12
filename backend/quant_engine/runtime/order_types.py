"""
多种订单类型支持 - 止损、止盈、条件单、冰山单、TWAP、VWAP、OCO
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class OrderType(Enum):
    """订单类型"""
    MARKET = "MARKET"  # 市价单
    LIMIT = "LIMIT"  # 限价单
    STOP = "STOP"  # 止损单
    STOP_LIMIT = "STOP_LIMIT"  # 止损限价单
    TAKE_PROFIT = "TAKE_PROFIT"  # 止盈单
    ICEBERG = "ICEBERG"  # 冰山单
    TWAP = "TWAP"  # 时间加权平均价格
    VWAP = "VWAP"  # 成交量加权平均价格
    OCO = "OCO"  # One-Cancels-the-Other


class OrderStatus(Enum):
    """订单状态"""
    PENDING = "PENDING"
    PARTIAL_FILLED = "PARTIAL_FILLED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


class Order:
    """订单基类"""
    
    def __init__(
        self,
        order_id: str,
        symbol: str,
        direction: str,
        volume: int,
        order_type: OrderType,
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
        take_profit_price: Optional[float] = None
    ):
        self.order_id = order_id
        self.symbol = symbol
        self.direction = direction  # BUY/SELL
        self.volume = volume
        self.order_type = order_type
        self.price = price
        self.stop_price = stop_price
        self.take_profit_price = take_profit_price
        self.status = OrderStatus.PENDING
        self.filled_volume = 0
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "order_id": self.order_id,
            "symbol": self.symbol,
            "direction": self.direction,
            "volume": self.volume,
            "order_type": self.order_type.value,
            "price": self.price,
            "stop_price": self.stop_price,
            "take_profit_price": self.take_profit_price,
            "status": self.status.value,
            "filled_volume": self.filled_volume,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }


class IcebergOrder(Order):
    """冰山单 - 大单拆分"""
    
    def __init__(
        self,
        order_id: str,
        symbol: str,
        direction: str,
        total_volume: int,
        display_volume: int,
        price: float
    ):
        super().__init__(order_id, symbol, direction, total_volume, OrderType.ICEBERG, price)
        self.display_volume = display_volume
        self.remaining_volume = total_volume
        self.child_orders: List[Order] = []
    
    def generate_child_order(self) -> Optional[Order]:
        """生成子订单"""
        if self.remaining_volume <= 0:
            return None
        
        child_volume = min(self.display_volume, self.remaining_volume)
        child_order_id = f"{self.order_id}_child_{len(self.child_orders)}"
        
        child_order = Order(
            child_order_id,
            self.symbol,
            self.direction,
            child_volume,
            OrderType.LIMIT,
            self.price
        )
        
        self.child_orders.append(child_order)
        self.remaining_volume -= child_volume
        
        return child_order


class TWAPOrder(Order):
    """TWAP订单 - 时间加权平均价格"""
    
    def __init__(
        self,
        order_id: str,
        symbol: str,
        direction: str,
        total_volume: int,
        duration_minutes: int,
        price_limit: Optional[float] = None
    ):
        super().__init__(order_id, symbol, direction, total_volume, OrderType.TWAP, price_limit)
        self.duration_minutes = duration_minutes
        self.price_limit = price_limit
        self.slices = self._calculate_slices()
        self.current_slice = 0
    
    def _calculate_slices(self) -> List[int]:
        """计算分片"""
        # 简化：平均分片
        num_slices = max(1, self.duration_minutes)
        base_volume = self.volume // num_slices
        remainder = self.volume % num_slices
        
        slices = [base_volume] * num_slices
        for i in range(remainder):
            slices[i] += 1
        
        return slices
    
    def get_next_slice(self) -> Optional[int]:
        """获取下一片"""
        if self.current_slice >= len(self.slices):
            return None
        
        volume = self.slices[self.current_slice]
        self.current_slice += 1
        return volume


class VWAPOrder(Order):
    """VWAP订单 - 成交量加权平均价格"""
    
    def __init__(
        self,
        order_id: str,
        symbol: str,
        direction: str,
        total_volume: int,
        target_vwap: float,
        price_limit: Optional[float] = None
    ):
        super().__init__(order_id, symbol, direction, total_volume, OrderType.VWAP, price_limit)
        self.target_vwap = target_vwap
        self.price_limit = price_limit
        self.executed_volume = 0
        self.executed_value = 0.0
    
    def get_current_vwap(self) -> float:
        """获取当前VWAP"""
        if self.executed_volume == 0:
            return 0.0
        return self.executed_value / self.executed_volume
    
    def should_execute(self, current_price: float, current_volume: int) -> bool:
        """判断是否应该执行"""
        # 简化逻辑：如果当前价格接近目标VWAP，则执行
        if self.price_limit and current_price > self.price_limit:
            return False
        
        return True


class OCOOrder(Order):
    """OCO订单 - One-Cancels-the-Other"""
    
    def __init__(
        self,
        order_id: str,
        symbol: str,
        direction: str,
        volume: int,
        stop_order: Order,
        take_profit_order: Order
    ):
        super().__init__(order_id, symbol, direction, volume, OrderType.OCO)
        self.stop_order = stop_order
        self.take_profit_order = take_profit_order
        self.filled_order: Optional[Order] = None
        self.cancelled_order: Optional[Order] = None
    
    def on_order_filled(self, order: Order):
        """订单成交回调"""
        if self.filled_order is None:
            self.filled_order = order
            self.status = OrderStatus.FILLED
            self.filled_volume = order.filled_volume
            
            # 取消另一个订单
            if order == self.stop_order:
                self.cancelled_order = self.take_profit_order
            else:
                self.cancelled_order = self.stop_order


class OrderManager:
    """订单管理器"""
    
    def __init__(self):
        self.orders: Dict[str, Order] = {}
        self.order_counter = 0
    
    def create_order(
        self,
        symbol: str,
        direction: str,
        volume: int,
        order_type: OrderType,
        **kwargs
    ) -> Order:
        """
        创建订单
        
        Parameters
        ----------
        symbol : str
            品种代码
        direction : str
            方向
        volume : int
            手数
        order_type : OrderType
            订单类型
        **kwargs
            其他参数
        
        Returns
        -------
        Order
            订单对象
        """
        self.order_counter += 1
        order_id = f"order_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{self.order_counter}"
        
        if order_type == OrderType.ICEBERG:
            order = IcebergOrder(
                order_id,
                symbol,
                direction,
                volume,
                kwargs.get("display_volume", 1),
                kwargs.get("price", 0)
            )
        elif order_type == OrderType.TWAP:
            order = TWAPOrder(
                order_id,
                symbol,
                direction,
                volume,
                kwargs.get("duration_minutes", 10),
                kwargs.get("price_limit")
            )
        elif order_type == OrderType.VWAP:
            order = VWAPOrder(
                order_id,
                symbol,
                direction,
                volume,
                kwargs.get("target_vwap", 0),
                kwargs.get("price_limit")
            )
        elif order_type == OrderType.OCO:
            stop_order = Order(
                f"{order_id}_stop",
                symbol,
                direction,
                volume,
                OrderType.STOP,
                stop_price=kwargs.get("stop_price")
            )
            take_profit_order = Order(
                f"{order_id}_tp",
                direction,
                symbol,
                volume,
                OrderType.TAKE_PROFIT,
                take_profit_price=kwargs.get("take_profit_price")
            )
            order = OCOOrder(order_id, symbol, direction, volume, stop_order, take_profit_order)
        else:
            order = Order(
                order_id,
                symbol,
                direction,
                volume,
                order_type,
                kwargs.get("price"),
                kwargs.get("stop_price"),
                kwargs.get("take_profit_price")
            )
        
        self.orders[order_id] = order
        logger.info(f"创建订单: {order_id} - {order_type.value}")
        
        return order
    
    def cancel_order(self, order_id: str) -> bool:
        """
        取消订单
        
        Parameters
        ----------
        order_id : str
            订单ID
        
        Returns
        -------
        bool
            是否成功
        """
        if order_id not in self.orders:
            logger.warning(f"订单不存在: {order_id}")
            return False
        
        order = self.orders[order_id]
        order.status = OrderStatus.CANCELLED
        order.updated_at = datetime.utcnow()
        
        logger.info(f"取消订单: {order_id}")
        return True
    
    def get_order(self, order_id: str) -> Optional[Order]:
        """
        获取订单
        
        Parameters
        ----------
        order_id : str
            订单ID
        
        Returns
        -------
        Optional[Order]
            订单对象
        """
        return self.orders.get(order_id)
    
    def get_orders_by_symbol(self, symbol: str) -> List[Order]:
        """
        获取品种的所有订单
        
        Parameters
        ----------
        symbol : str
            品种代码
        
        Returns
        -------
        List[Order]
            订单列表
        """
        return [o for o in self.orders.values() if o.symbol == symbol]
    
    def get_active_orders(self) -> List[Order]:
        """
        获取活跃订单
        
        Returns
        -------
        List[Order]
            活跃订单列表
        """
        return [o for o in self.orders.values() if o.status == OrderStatus.PENDING]
