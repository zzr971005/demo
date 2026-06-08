"""
仓位跟踪模块

提供仓位管理、盈亏计算、保证金计算等功能
"""

import logging
import threading
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum

logger = logging.getLogger("quant_engine.position_tracker")


class PositionDirection(Enum):
    """仓位方向"""
    LONG = "long"     # 多头
    SHORT = "short"   # 空头
    FLAT = "flat"     # 空仓


@dataclass
class Position:
    """仓位对象"""
    symbol: str
    direction: PositionDirection
    volume: int = 0
    avg_price: float = 0.0
    
    # 盈亏计算
    realized_pnl: float = 0.0      # 已实现盈亏
    unrealized_pnl: float = 0.0    # 未实现盈亏
    total_pnl: float = 0.0         # 总盈亏
    
    # 保证金
    margin: float = 0.0
    margin_rate: float = 0.12      # 默认12%保证金率
    
    # 费用
    total_commission: float = 0.0
    total_slippage: float = 0.0
    
    # 时间戳
    opened_at: Optional[datetime] = None
    last_trade_at: Optional[datetime] = None
    
    # 关联信息
    strategy_id: Optional[str] = None
    factor_id: Optional[str] = None
    
    @property
    def market_value(self) -> float:
        """市值"""
        return self.volume * self.avg_price
    
    @property
    def is_long(self) -> bool:
        """是否多头"""
        return self.direction == PositionDirection.LONG and self.volume > 0
    
    @property
    def is_short(self) -> bool:
        """是否空头"""
        return self.direction == PositionDirection.SHORT and self.volume > 0
    
    @property
    def is_flat(self) -> bool:
        """是否空仓"""
        return self.volume == 0
    
    def update_unrealized_pnl(self, current_price: float) -> None:
        """更新未实现盈亏"""
        if self.volume == 0:
            self.unrealized_pnl = 0.0
            return
        
        if self.direction == PositionDirection.LONG:
            self.unrealized_pnl = (current_price - self.avg_price) * self.volume
        else:
            self.unrealized_pnl = (self.avg_price - current_price) * self.volume
        
        self.total_pnl = self.realized_pnl + self.unrealized_pnl
    
    def update_margin(self, current_price: float) -> None:
        """更新保证金"""
        self.margin = current_price * self.volume * self.margin_rate


@dataclass
class TradeRecord:
    """交易记录"""
    trade_id: str
    symbol: str
    direction: str  # "open_long", "close_long", "open_short", "close_short"
    volume: int
    price: float
    commission: float
    timestamp: datetime
    pnl: float = 0.0  # 平仓盈亏


class PositionTracker:
    """仓位跟踪器"""
    
    def __init__(self):
        self._positions: Dict[str, Position] = {}  # symbol -> Position
        self._trade_history: List[TradeRecord] = []
        self._lock = threading.RLock()
        self._callbacks: List[Callable[[Position], None]] = []
        
        # 合约配置（合约乘数、保证金率等）
        self._contract_specs: Dict[str, Dict[str, Any]] = {
            "KQ.m@SHFE.rb": {"multiplier": 10, "margin_rate": 0.12, "tick_size": 1},
            "KQ.m@SHFE.hc": {"multiplier": 10, "margin_rate": 0.12, "tick_size": 1},
            "KQ.m@DCE.i": {"multiplier": 100, "margin_rate": 0.15, "tick_size": 0.5},
            "KQ.m@DCE.j": {"multiplier": 100, "margin_rate": 0.15, "tick_size": 0.5},
            "KQ.m@CZCE.TA": {"multiplier": 5, "margin_rate": 0.12, "tick_size": 2},
        }
    
    def get_position(self, symbol: str) -> Optional[Position]:
        """获取仓位"""
        with self._lock:
            return self._positions.get(symbol)
    
    def get_all_positions(self) -> List[Position]:
        """获取所有仓位"""
        with self._lock:
            return list(self._positions.values())
    
    def get_non_flat_positions(self) -> List[Position]:
        """获取非空仓位的列表"""
        with self._lock:
            return [p for p in self._positions.values() if not p.is_flat]
    
    def update_position(
        self,
        symbol: str,
        direction: str,  # "buy" or "sell"
        offset: str,     # "open" or "close"
        volume: int,
        price: float,
        commission: float = 0.0,
        strategy_id: Optional[str] = None,
        factor_id: Optional[str] = None,
    ) -> Position:
        """更新仓位"""
        with self._lock:
            # 获取或创建仓位
            if symbol not in self._positions:
                self._positions[symbol] = Position(
                    symbol=symbol,
                    direction=PositionDirection.FLAT,
                    strategy_id=strategy_id,
                    factor_id=factor_id,
                )
            
            position = self._positions[symbol]
            
            # 确定交易方向
            is_open = offset == "open"
            is_buy = direction == "buy"
            
            # 计算交易记录
            trade_pnl = 0.0
            
            if is_open:
                # 开仓
                if position.is_flat:
                    # 新开仓位
                    position.direction = PositionDirection.LONG if is_buy else PositionDirection.SHORT
                    position.avg_price = price
                    position.volume = volume
                    position.opened_at = datetime.now()
                elif (position.is_long and is_buy) or (position.is_short and not is_buy):
                    # 加仓
                    total_value = position.volume * position.avg_price + volume * price
                    position.volume += volume
                    position.avg_price = total_value / position.volume
                else:
                    # 反向开仓（先平后开）
                    logger.warning(f"Opening opposite position for {symbol}")
                    # 先平掉现有仓位
                    if position.volume > 0:
                        trade_pnl = self._calculate_close_pnl(position, position.volume, price)
                        position.realized_pnl += trade_pnl
                    
                    # 新开反向仓位
                    position.direction = PositionDirection.LONG if is_buy else PositionDirection.SHORT
                    position.avg_price = price
                    position.volume = volume
            else:
                # 平仓
                if position.is_flat:
                    logger.warning(f"Closing flat position for {symbol}")
                    return position
                
                if (position.is_long and not is_buy) or (position.is_short and is_buy):
                    # 正常平仓
                    close_volume = min(volume, position.volume)
                    trade_pnl = self._calculate_close_pnl(position, close_volume, price)
                    position.realized_pnl += trade_pnl
                    position.volume -= close_volume
                    
                    if position.volume == 0:
                        position.direction = PositionDirection.FLAT
                        position.avg_price = 0.0
                else:
                    # 反向平仓（实际上是在加仓）
                    logger.warning(f"Closing in wrong direction for {symbol}")
                    total_value = position.volume * position.avg_price + volume * price
                    position.volume += volume
                    position.avg_price = total_value / position.volume
            
            # 更新费用
            position.total_commission += commission
            position.last_trade_at = datetime.now()
            
            # 更新保证金
            position.update_margin(price)
            
            # 记录交易
            trade_direction = self._get_trade_direction(position.direction, is_open)
            trade_record = TradeRecord(
                trade_id=f"TRD{datetime.now().strftime('%Y%m%d%H%M%S')}",
                symbol=symbol,
                direction=trade_direction,
                volume=volume,
                price=price,
                commission=commission,
                timestamp=datetime.now(),
                pnl=trade_pnl,
            )
            self._trade_history.append(trade_record)
            
            # 更新总盈亏
            position.total_pnl = position.realized_pnl + position.unrealized_pnl
            
            logger.info(
                f"Updated position: {symbol} {position.direction.value} "
                f"vol={position.volume} avg_price={position.avg_price:.2f} "
                f"realized_pnl={position.realized_pnl:.2f}"
            )
            
            # 通知回调
            self._notify_callbacks(position)
            
            return position
    
    def _calculate_close_pnl(self, position: Position, volume: int, price: float) -> float:
        """计算平仓盈亏"""
        if position.direction == PositionDirection.LONG:
            return (price - position.avg_price) * volume
        else:
            return (position.avg_price - price) * volume
    
    def _get_trade_direction(self, position_direction: PositionDirection, is_open: bool) -> str:
        """获取交易方向描述"""
        if position_direction == PositionDirection.LONG:
            return "open_long" if is_open else "close_long"
        elif position_direction == PositionDirection.SHORT:
            return "open_short" if is_open else "close_short"
        else:
            return "unknown"
    
    def update_market_price(self, symbol: str, price: float) -> None:
        """更新市场价格（用于计算浮动盈亏）"""
        with self._lock:
            position = self._positions.get(symbol)
            if position and not position.is_flat:
                position.update_unrealized_pnl(price)
                position.update_margin(price)
                
                # 不通知回调，避免过于频繁的更新
    
    def close_position(
        self,
        symbol: str,
        price: float,
        commission: float = 0.0,
    ) -> Optional[Position]:
        """平仓"""
        with self._lock:
            position = self._positions.get(symbol)
            if not position or position.is_flat:
                logger.warning(f"No position to close for {symbol}")
                return None
            
            # 确定平仓方向
            close_direction = "sell" if position.is_long else "buy"
            
            return self.update_position(
                symbol=symbol,
                direction=close_direction,
                offset="close",
                volume=position.volume,
                price=price,
                commission=commission,
            )
    
    def get_position_summary(self) -> Dict[str, Any]:
        """获取仓位汇总"""
        with self._lock:
            positions = self.get_non_flat_positions()
            
            total_long_value = sum(p.market_value for p in positions if p.is_long)
            total_short_value = sum(p.market_value for p in positions if p.is_short)
            total_margin = sum(p.margin for p in positions)
            total_realized_pnl = sum(p.realized_pnl for p in positions)
            total_unrealized_pnl = sum(p.unrealized_pnl for p in positions)
            
            return {
                "total_positions": len(positions),
                "long_positions": len([p for p in positions if p.is_long]),
                "short_positions": len([p for p in positions if p.is_short]),
                "total_long_value": total_long_value,
                "total_short_value": total_short_value,
                "total_margin": total_margin,
                "total_realized_pnl": total_realized_pnl,
                "total_unrealized_pnl": total_unrealized_pnl,
                "total_pnl": total_realized_pnl + total_unrealized_pnl,
            }
    
    def get_trade_history(
        self,
        symbol: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[TradeRecord]:
        """获取交易历史"""
        with self._lock:
            trades = self._trade_history.copy()
            
            if symbol:
                trades = [t for t in trades if t.symbol == symbol]
            
            if start_time:
                trades = [t for t in trades if t.timestamp >= start_time]
            
            if end_time:
                trades = [t for t in trades if t.timestamp <= end_time]
            
            # 按时间倒序
            trades.sort(key=lambda x: x.timestamp, reverse=True)
            
            return trades[:limit]
    
    def add_callback(self, callback: Callable[[Position], None]) -> None:
        """添加仓位变更回调"""
        self._callbacks.append(callback)
    
    def remove_callback(self, callback: Callable[[Position], None]) -> None:
        """移除仓位变更回调"""
        if callback in self._callbacks:
            self._callbacks.remove(callback)
    
    def _notify_callbacks(self, position: Position) -> None:
        """通知回调"""
        for callback in self._callbacks:
            try:
                callback(position)
            except Exception as e:
                logger.error(f"Error in position callback: {e}")
    
    def reset(self) -> None:
        """重置所有仓位"""
        with self._lock:
            self._positions.clear()
            self._trade_history.clear()
            logger.info("All positions reset")


# 全局仓位跟踪器实例
_position_tracker: Optional[PositionTracker] = None


def get_position_tracker() -> PositionTracker:
    """获取全局仓位跟踪器实例"""
    global _position_tracker
    
    if _position_tracker is None:
        _position_tracker = PositionTracker()
    
    return _position_tracker


def reset_position_tracker() -> None:
    """重置全局仓位跟踪器实例"""
    global _position_tracker
    _position_tracker = None
