"""
TQSDK实时行情服务

提供实时行情数据订阅、缓存和分发功能
"""

import asyncio
import logging
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime
from collections import deque
import threading
from concurrent.futures import ThreadPoolExecutor

try:
    from tqsdk import TqApi, TqAuth
    from tqsdk.objs import Quote, Kline
    TQSDK_AVAILABLE = True
except ImportError:
    TQSDK_AVAILABLE = False
    logging.error("TQSDK not available - this system requires TQSDK to function")
    raise ImportError("TQSDK is required for this system")

logger = logging.getLogger("quant_engine.market_data")


@dataclass
class MarketData:
    """市场行情数据"""
    symbol: str
    timestamp: datetime
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    close: float = 0.0
    volume: int = 0
    amount: float = 0.0
    bid_price: float = 0.0
    bid_volume: int = 0
    ask_price: float = 0.0
    ask_volume: int = 0
    
    @classmethod
    def from_quote(cls, symbol: str, quote: Any) -> "MarketData":
        """从TQSDK Quote对象创建"""
        return cls(
            symbol=symbol,
            timestamp=datetime.now(),
            open=getattr(quote, 'open', 0.0),
            high=getattr(quote, 'high', 0.0),
            low=getattr(quote, 'low', 0.0),
            close=getattr(quote, 'last_price', 0.0),
            volume=getattr(quote, 'volume', 0),
            amount=getattr(quote, 'amount', 0.0),
            bid_price=getattr(quote, 'bid_price1', 0.0),
            bid_volume=getattr(quote, 'bid_volume1', 0),
            ask_price=getattr(quote, 'ask_price1', 0.0),
            ask_volume=getattr(quote, 'ask_volume1', 0),
        )


@dataclass
class KlineData:
    """K线数据"""
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    amount: float
    
    @classmethod
    def from_kline(cls, symbol: str, kline: Any) -> "KlineData":
        """从TQSDK Kline对象创建"""
        return cls(
            symbol=symbol,
            timestamp=datetime.fromtimestamp(kline.datetime / 1e9),
            open=kline.open,
            high=kline.high,
            low=kline.low,
            close=kline.close,
            volume=kline.volume,
            amount=kline.amount,
        )


class MarketDataCache:
    """行情数据缓存"""
    
    def __init__(self, max_history: int = 1000):
        self._cache: Dict[str, MarketData] = {}
        self._kline_cache: Dict[str, deque] = {}
        self._max_history = max_history
        self._lock = threading.RLock()
    
    def update_tick(self, data: MarketData) -> None:
        """更新Tick数据"""
        with self._lock:
            self._cache[data.symbol] = data
    
    def update_kline(self, data: KlineData) -> None:
        """更新K线数据"""
        with self._lock:
            if data.symbol not in self._kline_cache:
                self._kline_cache[data.symbol] = deque(maxlen=self._max_history)
            self._kline_cache[data.symbol].append(data)
    
    def get_tick(self, symbol: str) -> Optional[MarketData]:
        """获取最新Tick"""
        with self._lock:
            return self._cache.get(symbol)
    
    def get_klines(self, symbol: str, n: int = 100) -> List[KlineData]:
        """获取最近N根K线"""
        with self._lock:
            if symbol not in self._kline_cache:
                return []
            return list(self._kline_cache[symbol])[-n:]
    
    def get_all_ticks(self) -> Dict[str, MarketData]:
        """获取所有最新Tick"""
        with self._lock:
            return self._cache.copy()
    
    def clear(self) -> None:
        """清空缓存"""
        with self._lock:
            self._cache.clear()
            self._kline_cache.clear()


class MarketDataService:
    """TQSDK实时行情服务"""
    
    def __init__(
        self,
        account_id: Optional[str] = None,
        password: Optional[str] = None,
    ):
        if not TQSDK_AVAILABLE:
            raise RuntimeError("TQSDK is required for market data service")
        
        self.account_id = account_id
        self.password = password
        
        self._api: Optional[Any] = None
        self._cache = MarketDataCache()
        self._subscribed_symbols: set = set()
        self._callbacks: List[Callable[[MarketData], None]] = []
        self._kline_callbacks: List[Callable[[KlineData], None]] = []
        
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._executor = ThreadPoolExecutor(max_workers=2)
        
        # TQSDK对象引用
        self._quotes: Dict[str, Any] = {}
        self._klines: Dict[str, Any] = {}
    
    def connect(self) -> bool:
        """连接到TQSDK"""
        try:
            if self.account_id and self.password:
                self._api = TqApi(auth=TqAuth(self.account_id, self.password))
            else:
                logger.error("TQSDK account_id and password are required")
                return False
            
            logger.info("Connected to TQSDK")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to TQSDK: {e}")
            return False
    
    def disconnect(self) -> None:
        """断开连接"""
        self.stop()
        
        if self._api:
            try:
                self._api.close()
                logger.info("Disconnected from TQSDK")
            except Exception as e:
                logger.error(f"Error disconnecting: {e}")
            finally:
                self._api = None
    
    def subscribe(self, symbols: List[str], kline_period: int = 60) -> bool:
        """订阅行情"""
        if not self._api:
            logger.error("Not connected to TQSDK")
            return False
        
        for symbol in symbols:
            if symbol in self._subscribed_symbols:
                continue
            
            try:
                # 订阅Tick
                quote = self._api.get_quote(symbol)
                self._quotes[symbol] = quote
                
                # 订阅K线
                kline = self._api.get_kline_serial(symbol, kline_period)
                self._klines[symbol] = kline
                
                self._subscribed_symbols.add(symbol)
                logger.info(f"Subscribed: {symbol}")
                
            except Exception as e:
                logger.error(f"Failed to subscribe {symbol}: {e}")
                return False
        
        return True
    
    def unsubscribe(self, symbols: List[str]) -> None:
        """取消订阅"""
        for symbol in symbols:
            if symbol in self._subscribed_symbols:
                self._subscribed_symbols.discard(symbol)
                self._quotes.pop(symbol, None)
                self._klines.pop(symbol, None)
                logger.info(f"Unsubscribed: {symbol}")
    
    def add_tick_callback(self, callback: Callable[[MarketData], None]) -> None:
        """添加Tick数据回调"""
        self._callbacks.append(callback)
    
    def remove_tick_callback(self, callback: Callable[[MarketData], None]) -> None:
        """移除Tick数据回调"""
        if callback in self._callbacks:
            self._callbacks.remove(callback)
    
    def add_kline_callback(self, callback: Callable[[KlineData], None]) -> None:
        """添加K线数据回调"""
        self._kline_callbacks.append(callback)
    
    def start(self) -> None:
        """启动行情服务"""
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        logger.info("Market data service started")
    
    def stop(self) -> None:
        """停止行情服务"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None
        logger.info("Market data service stopped")
    
    def _run(self) -> None:
        """主循环"""
        while self._running:
            try:
                # 等待TQSDK更新
                self._api.wait_update(timeout=1)
                
                # 处理Tick更新
                for symbol, quote in self._quotes.items():
                    if self._api.is_changing(quote):
                        data = MarketData.from_quote(symbol, quote)
                        self._cache.update_tick(data)
                        self._notify_tick(data)
                
                # 处理K线更新
                for symbol, kline in self._klines.items():
                    if self._api.is_changing(kline.iloc[-1]):
                        data = KlineData.from_kline(symbol, kline.iloc[-1])
                        self._cache.update_kline(data)
                        self._notify_kline(data)
                        
            except Exception as e:
                logger.error(f"Error in market data loop: {e}")
                import time
                time.sleep(1)
    
    
    def _notify_tick(self, data: MarketData) -> None:
        """通知Tick更新"""
        for callback in self._callbacks:
            try:
                callback(data)
            except Exception as e:
                logger.error(f"Error in tick callback: {e}")
    
    def _notify_kline(self, data: KlineData) -> None:
        """通知K线更新"""
        for callback in self._kline_callbacks:
            try:
                callback(data)
            except Exception as e:
                logger.error(f"Error in kline callback: {e}")
    
    def get_tick(self, symbol: str) -> Optional[MarketData]:
        """获取最新Tick"""
        return self._cache.get_tick(symbol)
    
    def get_klines(self, symbol: str, n: int = 100) -> List[KlineData]:
        """获取最近N根K线"""
        return self._cache.get_klines(symbol, n)
    
    def get_all_ticks(self) -> Dict[str, MarketData]:
        """获取所有最新Tick"""
        return self._cache.get_all_ticks()


# 全局服务实例
_market_data_service: Optional[MarketDataService] = None


def get_market_data_service(
    account_id: Optional[str] = None,
    password: Optional[str] = None,
) -> MarketDataService:
    """获取全局行情服务实例"""
    global _market_data_service
    
    if _market_data_service is None:
        _market_data_service = MarketDataService(
            account_id=account_id,
            password=password,
        )
    
    return _market_data_service


def reset_market_data_service() -> None:
    """重置全局行情服务实例"""
    global _market_data_service
    
    if _market_data_service:
        _market_data_service.disconnect()
        _market_data_service = None
