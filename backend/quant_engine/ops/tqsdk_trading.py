"""
TQSDK交易引擎
集成TQKQ模拟账户进行交易执行
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional, List, Tuple
from enum import Enum

from tqsdk import TqApi, TqAuth, TqKq
from tqsdk.ta import MA, MACD, RSI, BOLL
import pandas as pd

logger = logging.getLogger(__name__)


class TradingMode(Enum):
    """交易模式"""
    PAPER = "paper"      # 模拟盘（TQKQ）
    LIVE = "live"        # 实盘


class OrderDirection(Enum):
    """下单方向"""
    BUY = "BUY"
    SELL = "SELL"


class OrderOffset(Enum):
    """开平方向"""
    OPEN = "OPEN"
    CLOSE = "CLOSE"
    CLOSE_TODAY = "CLOSE_TODAY"


class OrderStatus(Enum):
    """订单状态"""
    PENDING = "pending"
    PARTIAL = "partial"
    FILLED = "filled"
    CANCELLED = "cancelled"
    FAILED = "failed"


class TqsdkTradingEngine:
    """TQSDK交易引擎"""
    
    def __init__(self):
        self.api: Optional[TqApi] = None
        self.mode: TradingMode = TradingMode.PAPER
        self.connected = False
        self.account_info: Dict[str, Any] = {}
        self.positions: Dict[str, Dict[str, Any]] = {}
        
    def connect(self, mode: TradingMode = TradingMode.PAPER, 
                account_id: Optional[str] = None, 
                password: Optional[str] = None) -> bool:
        """
        连接TQSDK
        
        Args:
            mode: 交易模式（PAPER使用TQKQ模拟，LIVE使用实盘）
            account_id: 账户ID（新版TQSDK必需）
            password: 密码（新版TQSDK必需）
        
        Returns:
            是否连接成功
        """
        try:
            self.mode = mode
            
            # 新版TQSDK要求必须使用auth参数登录快期账户
            if not account_id or not password:
                logger.error("TQSDK需要账户ID和密码（新版TQSDK要求）")
                return False
            
            if mode == TradingMode.PAPER:
                # 使用TQKQ模拟账户（仍需auth登录）
                logger.info("连接TQKQ模拟账户...")
                self.api = TqApi(auth=TqAuth(account_id, password))
            else:
                # 使用实盘账户
                logger.info(f"连接实盘账户: {account_id}")
                self.api = TqApi(auth=TqAuth(account_id, password))
            
            self.connected = True
            logger.info("TQSDK连接成功")
            
            # 获取账户信息
            self._update_account_info()
            
            return True
            
        except Exception as e:
            logger.error(f"TQSDK连接失败: {e}", exc_info=True)
            self.connected = False
            return False
    
    def disconnect(self):
        """断开连接"""
        if self.api:
            try:
                self.api.close()
                logger.info("TQSDK连接已断开")
            except Exception as e:
                logger.error(f"断开连接失败: {e}", exc_info=True)
            self.api = None
            self.connected = False
    
    def _update_account_info(self):
        """更新账户信息"""
        if not self.api:
            return
        
        try:
            # 获取账户资产
            account = self.api.get_account()
            if account:
                self.account_info = {
                    "account_id": getattr(account, 'account_id', None),
                    "balance": getattr(account, 'balance', 0),
                    "available": getattr(account, 'available', 0),
                    "margin": getattr(account, 'margin', 0),
                    "frozen_margin": getattr(account, 'frozen_margin', 0),
                    "profit": getattr(account, 'profit', 0),
                    "risk_ratio": getattr(account, 'risk_ratio', 0),
                    "currency": getattr(account, 'currency', 'CNY'),
                }
            
            # 获取持仓
            positions = self.api.get_position()
            self.positions = {}
            for symbol, pos in positions.items():
                self.positions[symbol] = {
                    "symbol": symbol,
                    "volume_long": pos.volume_long,
                    "volume_short": pos.volume_short,
                    "open_price_long": pos.open_price_long,
                    "open_price_short": pos.open_price_short,
                    "margin_long": pos.margin_long,
                    "margin_short": pos.margin_short,
                    "profit_long": pos.profit_long,
                    "profit_short": pos.profit_short,
                }
            
            logger.debug(f"账户信息已更新: {self.account_info}")
            
        except Exception as e:
            logger.error(f"更新账户信息失败: {e}", exc_info=True)
    
    def get_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        获取行情报价
        
        Args:
            symbol: 合约代码，如 SHFE.rb2505
        
        Returns:
            报价信息字典
        """
        if not self.api or not self.connected:
            logger.error("TQSDK未连接")
            return None
        
        try:
            quote = self.api.get_quote(symbol)
            return {
                "symbol": symbol,
                "last_price": quote.last_price,
                "open": quote.open,
                "high": quote.high,
                "low": quote.low,
                "volume": quote.volume,
                "open_interest": quote.open_interest,
                "upper_limit": quote.upper_limit,
                "lower_limit": quote.lower_limit,
                "datetime": quote.datetime,
                "underlying_symbol": quote.underlying_symbol,
            }
        except Exception as e:
            logger.error(f"获取报价失败: {e}", exc_info=True)
            return None
    
    def insert_order(self, symbol: str, direction: OrderDirection, 
                     offset: OrderOffset, volume: int, 
                     limit_price: Optional[float] = None) -> Optional[str]:
        """
        下单
        
        Args:
            symbol: 合约代码
            direction: 买卖方向
            offset: 开平方向
            volume: 数量
            limit_price: 限价（None表示市价）
        
        Returns:
            订单ID
        """
        if not self.api or not self.connected:
            logger.error("TQSDK未连接")
            return None
        
        # IF合约禁止平今
        if "IF" in symbol and offset == OrderOffset.CLOSE_TODAY:
            logger.warning(f"IF合约禁止平今操作，自动转为平仓")
            offset = OrderOffset.CLOSE
        
        try:
            order = self.api.insert_order(
                symbol=symbol,
                direction=direction.value,
                offset=offset.value,
                volume=volume,
                limit_price=limit_price
            )
            
            logger.info(f"下单成功: {direction.value} {offset.value} {symbol} x {volume} @ {limit_price}")
            return order.order_id
            
        except Exception as e:
            logger.error(f"下单失败: {e}", exc_info=True)
            return None
    
    def cancel_order(self, order_id: str) -> bool:
        """
        撤单
        
        Args:
            order_id: 订单ID
        
        Returns:
            是否成功
        """
        if not self.api or not self.connected:
            logger.error("TQSDK未连接")
            return False
        
        try:
            self.api.cancel_order(order_id)
            logger.info(f"撤单成功: {order_id}")
            return True
        except Exception as e:
            logger.error(f"撤单失败: {e}", exc_info=True)
            return False
    
    def get_order_status(self, order_id: str) -> Optional[Dict[str, Any]]:
        """
        获取订单状态
        
        Args:
            order_id: 订单ID
        
        Returns:
            订单状态信息
        """
        if not self.api or not self.connected:
            logger.error("TQSDK未连接")
            return None
        
        try:
            orders = self.api.get_order(order_id)
            if orders:
                order = orders[order_id]
                return {
                    "order_id": order.order_id,
                    "symbol": order.symbol,
                    "direction": order.direction,
                    "offset": order.offset,
                    "volume": order.volume,
                    "original_volume": order.original_volume,
                    "price": order.price,
                    "status": order.status,
                    "filled_volume": order.filled_volume,
                    "create_time": order.create_time,
                    "update_time": order.update_time,
                }
            return None
        except Exception as e:
            logger.error(f"获取订单状态失败: {e}", exc_info=True)
            return None
    
    def calculate_margin(self, symbol: str, volume: int, 
                         direction: OrderDirection) -> Optional[float]:
        """
        计算保证金
        
        Args:
            symbol: 合约代码
            volume: 数量
            direction: 方向
        
        Returns:
            保证金金额
        """
        if not self.api or not self.connected:
            logger.error("TQSDK未连接")
            return None
        
        try:
            margin_info = self.api.calculate_margin(
                symbol=symbol,
                volume=volume,
                direction=direction.value
            )
            
            # 使用broker_margin（包含期货公司加收）
            if direction == OrderDirection.BUY:
                return margin_info.margin_long_broker
            else:
                return margin_info.margin_short_broker
                
        except Exception as e:
            logger.error(f"计算保证金失败: {e}", exc_info=True)
            return None
    
    def get_kline(self, symbol: str, duration_seconds: int, 
                  start_dt: Optional[datetime] = None, 
                  end_dt: Optional[datetime] = None,
                  count: Optional[int] = None) -> Optional[pd.DataFrame]:
        """
        获取K线数据
        
        Args:
            symbol: 合约代码
            duration_seconds: K线周期（秒）
            start_dt: 开始时间
            end_dt: 结束时间
            count: K线数量（与时间范围二选一）
        
        Returns:
            K线DataFrame
        """
        if not self.api or not self.connected:
            logger.error("TQSDK未连接")
            return None
        
        try:
            if count:
                kline = self.api.get_kline_serial(symbol, duration_seconds, count=count)
            else:
                kline = self.api.get_kline_serial(symbol, duration_seconds)
            
            df = pd.DataFrame({
                "datetime": kline["datetime"],
                "open": kline["open"],
                "high": kline["high"],
                "low": kline["low"],
                "close": kline["close"],
                "volume": kline["volume"],
            })
            
            # 如果指定了时间范围，进行过滤
            if start_dt:
                df = df[df["datetime"] >= start_dt]
            if end_dt:
                df = df[df["datetime"] <= end_dt]
            
            return df
            
        except Exception as e:
            logger.error(f"获取K线数据失败: {e}", exc_info=True)
            return None
    
    def wait_update(self, timeout: Optional[float] = None) -> bool:
        """
        等待数据更新
        
        Args:
            timeout: 超时时间（秒）
        
        Returns:
            是否有数据更新
        """
        if not self.api or not self.connected:
            logger.error("TQSDK未连接")
            return False
        
        try:
            if timeout:
                return self.api.wait_update(timeout=timeout)
            else:
                self.api.wait_update()
                return True
        except Exception as e:
            logger.error(f"等待更新失败: {e}", exc_info=True)
            return False
    
    def get_account_info(self) -> Dict[str, Any]:
        """获取账户信息"""
        return self.account_info
    
    def get_positions(self) -> Dict[str, Dict[str, Any]]:
        """获取持仓"""
        return self.positions
    
    def get_status(self) -> Dict[str, Any]:
        """获取引擎状态"""
        return {
            "connected": self.connected,
            "mode": self.mode.value,
            "account_info": self.account_info,
            "position_count": len(self.positions),
        }


# 全局交易引擎实例
_trading_engine = TqsdkTradingEngine()


def get_trading_engine() -> TqsdkTradingEngine:
    """获取全局交易引擎实例"""
    return _trading_engine


def init_trading_engine(mode: TradingMode = TradingMode.PAPER,
                        account_id: Optional[str] = None,
                        password: Optional[str] = None) -> bool:
    """
    初始化交易引擎
    
    Args:
        mode: 交易模式
        account_id: 账户ID（实盘模式）
        password: 密码（实盘模式）
    
    Returns:
        是否初始化成功
    """
    global _trading_engine
    return _trading_engine.connect(mode, account_id, password)


def shutdown_trading_engine():
    """关闭交易引擎"""
    global _trading_engine
    _trading_engine.disconnect()
