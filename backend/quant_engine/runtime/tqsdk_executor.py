"""
TQSDK交易执行器

对接天勤SDK实现实盘交易功能
"""

import logging
import threading
import time
from typing import Dict, List, Optional, Callable, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

try:
    from tqsdk import TqApi, TqAuth, TqKq
    from tqsdk.objs import Order as TqOrder, Trade as TqTrade, Position as TqPosition
    TQSDK_AVAILABLE = True
except ImportError:
    TQSDK_AVAILABLE = False
    logging.warning("TQSDK not available, trading will be in mock mode")

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

logger = logging.getLogger("quant_engine.tqsdk_executor")


@dataclass
class TqsdkConfig:
    """TQSDK配置"""
    account_id: Optional[str] = None
    password: Optional[str] = None
    mock: bool = False
    
    # 交易参数
    default_price_tick: float = 1.0
    default_lots: int = 1
    
    # 超时配置
    order_timeout_seconds: int = 30
    connect_timeout_seconds: int = 10


class TqsdkExecutor:
    """TQSDK交易执行器"""
    
    def __init__(
        self,
        order_manager: Optional[OrderManager] = None,
        position_tracker: Optional[PositionTracker] = None,
        config: Optional[TqsdkConfig] = None,
    ):
        self.order_manager = order_manager or get_order_manager()
        self.position_tracker = position_tracker or get_position_tracker()
        self.config = config or TqsdkConfig()
        
        # TQSDK实例
        self._api: Optional[Any] = None
        self._account: Optional[Any] = None
        
        # 订单映射：系统订单ID -> TQSDK订单对象
        self._order_map: Dict[str, Any] = {}
        self._lock = threading.RLock()
        
        # 运行状态
        self._running = False
        self._connected = False
        
        # 回调
        self._callbacks: List[Callable[[str, Dict[str, Any]], None]] = []
        
        # 监控线程
        self._monitor_thread: Optional[threading.Thread] = None
        
        # 合约映射缓存
        self._contract_cache: Dict[str, Any] = {}
    
    def connect(self) -> bool:
        """连接TQSDK"""
        if not TQSDK_AVAILABLE:
            logger.warning("TQSDK not available, running in mock mode")
            self._connected = True
            return True
        
        try:
            if self.config.mock or not self.config.account_id:
                # 使用模拟账户
                logger.info("Connecting to TQSDK mock account...")
                self._api = TqApi(TqKq())
            else:
                # 使用实盘账户
                logger.info(f"Connecting to TQSDK with account {self.config.account_id}...")
                self._api = TqApi(
                    auth=TqAuth(self.config.account_id, self.config.password)
                )
            
            # 获取账户信息
            self._account = self._api.get_account()
            
            self._connected = True
            logger.info("TQSDK connected successfully")
            
            # 启动监控线程
            self._start_monitor()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to TQSDK: {e}")
            self._connected = False
            return False
    
    def disconnect(self) -> None:
        """断开连接"""
        self._running = False
        
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
        
        if self._api:
            try:
                self._api.close()
                logger.info("TQSDK disconnected")
            except Exception as e:
                logger.error(f"Error disconnecting TQSDK: {e}")
        
        self._connected = False
        self._api = None
    
    def is_connected(self) -> bool:
        """检查连接状态"""
        return self._connected and self._api is not None
    
    def _start_monitor(self) -> None:
        """启动订单监控线程"""
        self._running = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        logger.info("Order monitor started")
    
    def _monitor_loop(self) -> None:
        """监控循环"""
        while self._running:
            try:
                if self._api and TQSDK_AVAILABLE:
                    # 等待数据更新
                    self._api.wait_update(timeout=1)
                    
                    # 检查订单状态变化
                    self._check_order_updates()
                    
                    # 检查成交回报
                    self._check_trade_updates()
                    
                    # 更新持仓信息
                    self._update_positions()
                else:
                    time.sleep(1)
                    
            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")
                time.sleep(1)
    
    def _check_order_updates(self) -> None:
        """检查订单状态更新"""
        with self._lock:
            for order_id, tq_order in list(self._order_map.items()):
                try:
                    # 获取系统订单
                    order = self.order_manager.get_order(order_id)
                    if not order or order.is_completed:
                        continue
                    
                    # 检查TQSDK订单状态
                    if hasattr(tq_order, 'status'):
                        tq_status = tq_order.status
                        
                        # 映射状态
                        if tq_status == "FINISHED":
                            if tq_order.volume_left == 0:
                                # 全部成交
                                pass  # 成交在_trade_updates中处理
                            else:
                                # 部分成交后结束（撤单）
                                self.order_manager.cancel_order(
                                    order_id, 
                                    f"Order cancelled in TQSDK, filled: {tq_order.volume_orign - tq_order.volume_left}"
                                )
                        elif tq_status == "ALIVE":
                            # 检查是否部分成交
                            filled_vol = tq_order.volume_orign - tq_order.volume_left
                            if filled_vol > order.filled_volume:
                                # 有新的成交
                                pass  # 成交在_trade_updates中处理
                                
                except Exception as e:
                    logger.error(f"Error checking order {order_id}: {e}")
    
    def _check_trade_updates(self) -> None:
        """检查成交回报"""
        if not self._api:
            return
        
        try:
            # 获取所有成交
            trades = self._api.get_trade()
            
            for trade in trades.values():
                # 查找对应的系统订单
                with self._lock:
                    for order_id, tq_order in self._order_map.items():
                        if tq_order.order_id == trade.order_id:
                            # 处理成交
                            self._process_trade(order_id, trade)
                            break
                            
        except Exception as e:
            logger.error(f"Error checking trade updates: {e}")
    
    def _process_trade(self, order_id: str, trade: Any) -> None:
        """处理成交"""
        try:
            # 计算手续费（简化处理）
            commission = trade.volume * trade.price * 0.0001  # 万分之一
            
            # 记录成交
            self.order_manager.fill_order(
                order_id=order_id,
                volume=trade.volume,
                price=trade.price,
                commission=commission,
            )
            
            # 获取订单信息
            order = self.order_manager.get_order(order_id)
            if order:
                # 更新仓位
                direction = "buy" if order.direction == OrderDirection.BUY else "sell"
                offset = "open" if order.offset == OrderOffset.OPEN else "close"
                
                self.position_tracker.update_position(
                    symbol=order.symbol,
                    direction=direction,
                    offset=offset,
                    volume=trade.volume,
                    price=trade.price,
                    commission=commission,
                    strategy_id=order.strategy_id,
                    factor_id=order.factor_id,
                )
                
                logger.info(
                    f"Trade processed: {order.symbol} {direction} {trade.volume}@{trade.price}"
                )
                
        except Exception as e:
            logger.error(f"Error processing trade: {e}")
    
    def _update_positions(self) -> None:
        """更新持仓信息"""
        if not self._api:
            return
        
        try:
            # 获取TQSDK持仓
            positions = self._api.get_position()
            
            for pos in positions.values():
                symbol = self._convert_from_tq_symbol(pos.exchange_id, pos.instrument_id)
                
                # 更新市场价格以计算浮动盈亏
                quote = self._api.get_quote(f"{pos.exchange_id}.{pos.instrument_id}")
                if quote:
                    self.position_tracker.update_market_price(symbol, quote.last_price)
                    
        except Exception as e:
            logger.error(f"Error updating positions: {e}")
    
    def submit_order(self, order_id: str) -> bool:
        """提交订单到TQSDK"""
        if not self.is_connected():
            logger.error("TQSDK not connected")
            return False
        
        if not TQSDK_AVAILABLE:
            logger.warning("TQSDK not available, order will be simulated")
            return self._simulate_order(order_id)
        
        order = self.order_manager.get_order(order_id)
        if not order:
            logger.error(f"Order not found: {order_id}")
            return False
        
        try:
            # 转换合约代码
            tq_symbol = self._convert_to_tq_symbol(order.symbol)
            
            # 确定买卖方向
            direction = "BUY" if order.direction == OrderDirection.BUY else "SELL"
            
            # 确定开平方向
            if order.offset == OrderOffset.OPEN:
                offset = "OPEN"
            elif order.offset == OrderOffset.CLOSE:
                offset = "CLOSE"
            else:
                offset = "CLOSETODAY"
            
            # 确定价格类型
            if order.order_type == OrderType.MARKET:
                # 市价单
                tq_order = self._api.insert_order(
                    symbol=tq_symbol,
                    direction=direction,
                    offset=offset,
                    volume=order.volume,
                )
            else:
                # 限价单
                if order.price is None:
                    logger.error(f"Limit order {order_id} has no price")
                    return False
                
                tq_order = self._api.insert_order(
                    symbol=tq_symbol,
                    direction=direction,
                    offset=offset,
                    volume=order.volume,
                    limit_price=order.price,
                )
            
            # 保存映射
            with self._lock:
                self._order_map[order_id] = tq_order
            
            # 更新订单状态
            self.order_manager.submit_order(order_id)
            
            logger.info(f"Order {order_id} submitted to TQSDK")
            return True
            
        except Exception as e:
            logger.error(f"Failed to submit order {order_id}: {e}")
            self.order_manager.reject_order(order_id, str(e))
            return False
    
    def cancel_order(self, order_id: str) -> bool:
        """取消订单"""
        if not self.is_connected():
            logger.error("TQSDK not connected")
            return False
        
        if not TQSDK_AVAILABLE:
            logger.warning("TQSDK not available, order will be cancelled locally")
            return self.order_manager.cancel_order(order_id, "Simulated cancel")
        
        try:
            with self._lock:
                tq_order = self._order_map.get(order_id)
                if not tq_order:
                    logger.error(f"TQSDK order not found: {order_id}")
                    return False
                
                # 取消订单
                self._api.cancel_order(tq_order)
            
            logger.info(f"Order {order_id} cancelled in TQSDK")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cancel order {order_id}: {e}")
            return False
    
    def _simulate_order(self, order_id: str) -> bool:
        """模拟订单执行（当TQSDK不可用时）"""
        import random
        import time
        
        order = self.order_manager.get_order(order_id)
        if not order:
            return False
        
        # 模拟提交
        self.order_manager.submit_order(order_id)
        
        # 模拟成交（在新线程中）
        def simulate_fill():
            time.sleep(random.uniform(0.5, 2.0))  # 随机延迟
            
            # 模拟部分成交或全部成交
            fill_volume = order.volume
            fill_price = order.price or 3500.0  # 默认价格
            
            self.order_manager.fill_order(
                order_id=order_id,
                volume=fill_volume,
                price=fill_price,
                commission=fill_volume * fill_price * 0.0001,
            )
            
            # 更新仓位
            direction = "buy" if order.direction == OrderDirection.BUY else "sell"
            offset = "open" if order.offset == OrderOffset.OPEN else "close"
            
            self.position_tracker.update_position(
                symbol=order.symbol,
                direction=direction,
                offset=offset,
                volume=fill_volume,
                price=fill_price,
                commission=fill_volume * fill_price * 0.0001,
                strategy_id=order.strategy_id,
                factor_id=order.factor_id,
            )
        
        threading.Thread(target=simulate_fill, daemon=True).start()
        
        return True
    
    def _convert_to_tq_symbol(self, symbol: str) -> str:
        """将系统合约代码转换为TQSDK格式"""
        # 系统格式: KQ.m@SHFE.rb
        # TQSDK格式: SHFE.rb2010 (需要具体合约)
        
        if symbol.startswith("KQ.m@"):
            # 主连合约，需要获取具体合约
            parts = symbol.replace("KQ.m@", "").split(".")
            if len(parts) == 2:
                exchange, product = parts
                # 这里简化处理，实际应该查询当前主力合约
                return f"{exchange}.{product}2501"
        
        return symbol
    
    def _convert_from_tq_symbol(self, exchange_id: str, instrument_id: str) -> str:
        """将TQSDK合约代码转换为系统格式"""
        # 简化处理
        return f"KQ.m@{exchange_id}.{instrument_id[:2]}"
    
    def get_account_info(self) -> Dict[str, Any]:
        """获取账户信息"""
        if not self._account or not TQSDK_AVAILABLE:
            return {
                "connected": self._connected,
                "balance": 0.0,
                "available": 0.0,
                "margin": 0.0,
            }
        
        try:
            return {
                "connected": self._connected,
                "balance": float(self._account.balance),
                "available": float(self._account.available),
                "margin": float(self._account.margin),
                "float_profit": float(self._account.float_profit),
                "position_profit": float(self._account.position_profit),
                "close_profit": float(self._account.close_profit),
                "commission": float(self._account.commission),
                "preminum": float(self._account.premium),
                "risk_ratio": float(self._account.ratio) if hasattr(self._account, 'ratio') else 0.0,
            }
        except Exception as e:
            logger.error(f"Error getting account info: {e}")
            return {"connected": self._connected, "error": str(e)}
    
    def get_tq_positions(self) -> List[Dict[str, Any]]:
        """获取TQSDK持仓"""
        if not self._api or not TQSDK_AVAILABLE:
            return []
        
        try:
            positions = self._api.get_position()
            result = []
            
            for pos in positions.values():
                result.append({
                    "symbol": f"{pos.exchange_id}.{pos.instrument_id}",
                    "direction": "long" if pos.pos_long > 0 else "short",
                    "volume": pos.pos_long if pos.pos_long > 0 else pos.pos_short,
                    "open_price": float(pos.open_price_long if pos.pos_long > 0 else pos.open_price_short),
                    "float_profit": float(pos.float_profit_long if pos.pos_long > 0 else pos.float_profit_short),
                    "margin": float(pos.margin_long if pos.pos_long > 0 else pos.margin_short),
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return []


# 全局执行器实例
_executor: Optional[TqsdkExecutor] = None


def get_tqsdk_executor(
    order_manager: Optional[OrderManager] = None,
    position_tracker: Optional[PositionTracker] = None,
    config: Optional[TqsdkConfig] = None,
) -> TqsdkExecutor:
    """获取全局执行器实例"""
    global _executor
    
    if _executor is None:
        _executor = TqsdkExecutor(order_manager, position_tracker, config)
    
    return _executor


def reset_tqsdk_executor() -> None:
    """重置全局执行器实例"""
    global _executor
    if _executor:
        _executor.disconnect()
    _executor = None
