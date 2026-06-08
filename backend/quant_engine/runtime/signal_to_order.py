"""
信号到订单转换器
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


class SignalType(Enum):
    """信号类型"""
    BUY = "BUY"
    SELL = "SELL"
    CLOSE = "CLOSE"
    HOLD = "HOLD"


class OrderType(Enum):
    """订单类型"""
    MARKET = "MARKET"  # 市价单
    LIMIT = "LIMIT"  # 限价单
    STOP = "STOP"  # 止损单
    STOP_LIMIT = "STOP_LIMIT"  # 止损限价单


class SignalToOrderConverter:
    """信号到订单转换器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化转换器
        
        Parameters
        ----------
        config : Dict[str, Any]
            配置字典
        """
        self.config = config or {}
        self.default_order_type = OrderType.MARKET
        
    def convert_signal_to_order(
        self,
        signal: Dict[str, Any],
        current_position: Optional[Dict[str, Any]] = None,
        market_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        将信号转换为订单
        
        Parameters
        ----------
        signal : Dict[str, Any]
            信号字典
        current_position : Optional[Dict[str, Any]]
            当前持仓
        market_data : Optional[Dict[str, Any]]
            市场数据
        
        Returns
        -------
        Dict[str, Any]
            订单字典
        """
        signal_type = SignalType(signal.get("signal_type", "HOLD"))
        symbol = signal.get("symbol")
        volume = signal.get("volume", 0)
        
        if signal_type == SignalType.HOLD:
            return {"action": "hold", "reason": "信号为持有"}
        
        if signal_type == SignalType.CLOSE:
            return self._create_close_order(symbol, current_position, market_data)
        
        if signal_type == SignalType.BUY:
            return self._create_buy_order(symbol, volume, current_position, market_data)
        
        if signal_type == SignalType.SELL:
            return self._create_sell_order(symbol, volume, current_position, market_data)
        
        return {"action": "hold", "reason": "未知信号类型"}
    
    def _create_buy_order(
        self,
        symbol: str,
        volume: int,
        current_position: Optional[Dict[str, Any]],
        market_data: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """创建买入订单"""
        if volume <= 0:
            return {"action": "hold", "reason": "手数无效"}
        
        order = {
            "symbol": symbol,
            "direction": "BUY",
            "offset": "OPEN",
            "volume": volume,
            "order_type": self.default_order_type.value,
            "price": None,
            "created_at": datetime.utcnow()
        }
        
        # 如果有市场数据，可以设置限价
        if market_data:
            current_price = market_data.get("last_price")
            if current_price and self.default_order_type == OrderType.LIMIT:
                order["price"] = current_price
                order["order_type"] = OrderType.LIMIT.value
        
        logger.info(f"创建买入订单: {symbol} {volume}手")
        return order
    
    def _create_sell_order(
        self,
        symbol: str,
        volume: int,
        current_position: Optional[Dict[str, Any]],
        market_data: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """创建卖出订单"""
        if volume <= 0:
            return {"action": "hold", "reason": "手数无效"}
        
        order = {
            "symbol": symbol,
            "direction": "SELL",
            "offset": "OPEN",
            "volume": volume,
            "order_type": self.default_order_type.value,
            "price": None,
            "created_at": datetime.utcnow()
        }
        
        # 如果有市场数据，可以设置限价
        if market_data:
            current_price = market_data.get("last_price")
            if current_price and self.default_order_type == OrderType.LIMIT:
                order["price"] = current_price
                order["order_type"] = OrderType.LIMIT.value
        
        logger.info(f"创建卖出订单: {symbol} {volume}手")
        return order
    
    def _create_close_order(
        self,
        symbol: str,
        current_position: Optional[Dict[str, Any]],
        market_data: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """创建平仓订单"""
        if not current_position:
            return {"action": "hold", "reason": "无持仓可平"}
        
        volume = current_position.get("volume", 0)
        direction = current_position.get("direction", "LONG")
        
        if volume <= 0:
            return {"action": "hold", "reason": "持仓手数无效"}
        
        # 确定平仓方向
        close_direction = "SELL" if direction == "LONG" else "BUY"
        
        order = {
            "symbol": symbol,
            "direction": close_direction,
            "offset": "CLOSE",
            "volume": volume,
            "order_type": self.default_order_type.value,
            "price": None,
            "created_at": datetime.utcnow()
        }
        
        # 如果有市场数据，可以设置限价
        if market_data:
            current_price = market_data.get("last_price")
            if current_price and self.default_order_type == OrderType.LIMIT:
                order["price"] = current_price
                order["order_type"] = OrderType.LIMIT.value
        
        logger.info(f"创建平仓订单: {symbol} {volume}手 {close_direction}")
        return order
    
    def batch_convert_signals(
        self,
        signals: List[Dict[str, Any]],
        positions: Dict[str, Dict[str, Any]],
        market_data: Dict[str, Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        批量转换信号
        
        Parameters
        ----------
        signals : List[Dict[str, Any]]
            信号列表
        positions : Dict[str, Dict[str, Any]]
            持仓字典
        market_data : Dict[str, Dict[str, Any]]
            市场数据字典
        
        Returns
        -------
        List[Dict[str, Any]]
            订单列表
        """
        orders = []
        
        for signal in signals:
            symbol = signal.get("symbol")
            current_position = positions.get(symbol)
            symbol_market_data = market_data.get(symbol)
            
            order = self.convert_signal_to_order(
                signal,
                current_position,
                symbol_market_data
            )
            
            if order.get("action") != "hold":
                orders.append(order)
        
        logger.info(f"批量转换信号: {len(signals)}个信号 -> {len(orders)}个订单")
        return orders
